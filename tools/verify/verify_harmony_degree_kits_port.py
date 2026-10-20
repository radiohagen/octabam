#!/usr/bin/env python3
"""Real Kit recall with degree locks, incoming defaults and a held physical root."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
import verify_kits as kits
from verify_harmony_degree_scenes_port import write_scene_file
import verify_midi_harmony_port as p

B=0x400e21e0
PS=0x18b2


def recall(source,outgoing,incoming,target,sym,scenes=False,size=0):
    name=f'{outgoing}-to-{incoming}-kit{target+1}'+(f'-size{size+1}' if size else '')
    w=p.fixture(source,name,{0:outgoing},key_raw=2,first_note=48)
    for path in (w/'project').glob('project.*'):
        path.write_bytes(re.sub(rb'(?m)^BANK=\d+',b'BANK=0',path.read_bytes()))
    for path in (w/'project').glob('bank*.work'):
        bank=int(path.stem[4:])
        def seed(data):
            for part in range(8):
                base=p.otp.PART_BASE+part*p.otp.PART_STRIDE+9
                for track in range(8):data[base+0x4e2+track*36+19]=35
                if bank==target//4+1 and part%4==target%4:
                    for field,value in ((5,incoming),(17,6),(18,1+(size<<3)),(19,39)):
                        data[base+0x4e2+field]=value
                    data[base+0x3e2]=65
                if scenes:
                    selected=bank==target//4+1 and part%4==target%4
                    mode=incoming if selected else outgoing
                    endpoints=(38,42) if selected and mode else (55,62) if selected else (35,39) if mode else (48,55)
                    data[base+0x10:base+0x12]=bytes((0,1))

            at=0x492e+0x39
            data[at+2*32]=48
            for step in (4,8):data[at+step*32]=255
            for step in (2,4,8):data[at+step*32+3:at+step*32+6]=b'\xff'*3
        p.otp._bank_write(w/'project',bank,seed,guard=False)
    if scenes:
        tables={}
        for context in range(64):
            mode=incoming if context==target else outgoing
            endpoints=(38,42) if context==target and mode else (55,62) if context==target else (35,39) if mode else (48,55)
            tables[context]=[(0,endpoints[0]),(256,endpoints[1])]
        write_scene_file(w/'project',tables)
    card,_=p.emu_card.stage_project(w/'project','OCTABAM','BASS',tree=w/'seed-tree')
    (w/'card.img').write_bytes(card)
    script=kits.Script()
    script.tap('no');script.down(0,400)
    script.tap('part',800)
    for _ in range(target):script.tap('down',120)
    script.tap('yes',1500);script.up(0,800)
    script.tap(2,600)
    script.tap('play',3500);script.tap('stop',1200)
    panel=w/'recall.txt';panel.write_text(script.text())
    lock=sym['ch_lock_table']
    library=sym['KIMG']+kits.O_LIB
    before=f'{B:#x},0x9b340={w}/before-bank.bin;{library:#x},{kits.REC*64}={w}/before-library.bin'
    after=(f'{B:#x},0x9b340={w}/after-bank.bin;{library:#x},{kits.REC*64}={w}/after-library.bin;'
           f'{sym["KIMG"]+kits.O_ASSIGN:#x},1={w}/assignment.bin;'
           f'{sym["hd_banks"]:#x},16768={w}/degrees.bin;{lock:#x},8192={w}/chrd.bin;'
           f'{sym["mh_refs"]:#x},1024={w}/refs.bin')
    steps=['--step','-:poke:0x80000015=1;0x460d16f3=1;0x100b14cc=0',
           '--step',f'-:call:{sym["hd_sync_c"]:#x},0,0,0',
           '--step',f'-:poke:{lock+2:#x}=5']
    if outgoing:steps+=['--step',f'-:call:{sym["hd_edit_step_c"]:#x},0,0,0,2,35']
    if scenes:steps+=['--step','-:poke:0x460d16c8=0;0x460d16c9=0;0x460d16ca=0;0x460d16cb=0']
    events=p.run(w,'recall',steps+['--step','-:dump:'+before,'--internal-clock',
                                  '--live-script',panel,'--mem-dump',after])
    p.balanced(events)
    notes=[e[2] for e in events if e[:2]==('on',1)]
    held=[48,51,55] if outgoing==2 else [48]
    live=[50,53,57,60] if incoming==2 else [50]
    root=50 if outgoing else 48
    sequence=([48,65,65] if incoming==0 else [root,57,57] if incoming==1 else
              [root,root+4,root+7]+[57,60,64,67]*2)
    if scenes:sequence=([62]*3 if incoming<2 else [62,66,69]+[62,65,69,72]*2)
    if size==3 and incoming==2:
        sequence=([62,66,69,74]+[62,65,69,72]*2 if scenes else
                  [root,root+4,root+7,root+12]+[57,60,64,67]*2)
    assert notes==held+live+sequence,(name,notes,held+live+sequence)
    assert (w/'assignment.bin').read_bytes()==bytes((target,)),name
    bank=(w/'after-bank.bin').read_bytes()
    part=bank[0x8e57];assert part<4
    setup=0x8ed80+part*PS+0x4e2
    for field,value in ((5,incoming),(17,6),(18,1+(size<<3)),(19,39)):
        assert bank[setup+field]==value,(name,field,bank[setup+field])
    assert bank[setup-0x100]==65
    assert bank[0x4900+2*32]==(47 if incoming and not outgoing else 48)  # canonical HARM mirror
    assert bank[0x4900+4*32]==bank[0x4900+8*32]==255
    degrees=(w/'degrees.bin').read_bytes()
    assert degrees[2]==((35 if outgoing else 34) if incoming else 255)
    assert degrees[4]==degrees[8]==255
    assert (w/'chrd.bin').read_bytes()==b'\xff'*2+b'\x05'+b'\xff'*8189
    assert (w/'before-library.bin').read_bytes()==(w/'after-library.bin').read_bytes(), 'recall rewrote library'
    assert (w/'refs.bin').read_bytes()==bytes(1024)
    print(f'[ok] {name}: held releases drained, explicit DEG/CHRD retained, incoming defaults used',flush=True)
    return dict(notes=notes,part=part+1,library_unchanged=True,held_releases_balanced=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',required=True,type=Path)
    ap.add_argument('--frozen',action='store_true',help='reuse the image and symbols from the previous run')
    ap.add_argument('--scenes',action='store_true',help='test incoming scene roots on every Kit mode pair')
    ap.add_argument('--size-four',action='store_true',help='incoming Kit recalls SIZE 4 alongside its CHRD default')
    ap.add_argument('--case',action='append',choices=[f'{a}-{b}-{t}' for a in range(3) for b in range(3) for t in (2,6)])
    args=ap.parse_args()
    p.OUT=p.ROOT/('out/degree-scenes-kits-port' if args.scenes else 'out/degree-kits-port');p.OUT.mkdir(parents=True,exist_ok=True)
    if args.frozen:
        p.CANDIDATE_IMAGE=p.OUT/'candidate.bin'
        sym=json.loads((p.OUT/'candidate-all-symbols.json').read_text())
        p.harmony.symbols=lambda:sym
    else:
        p.freeze_candidate(p.OUT)
        raw=subprocess.check_output(['m68k-elf-nm',str(p.ROOT/'out/platform/runtime/runtime.elf')],text=True)
        sym={f[2]:int(f[0],16) for line in raw.splitlines() if len(f:=line.split())==3}
        (p.OUT/'candidate-all-symbols.json').write_text(json.dumps(sym,indent=2)+'\n')
    assert all(k in sym for k in ('KIMG','hd_banks','ch_lock_table'))
    if 'scn_lib' in sym:kits.REC=kits.REC1+4096
    selected=args.case or [f'{a}-{b}-{t}' for a in range(3) for b in range(3) for t in (2,6)]
    results={}
    for case in selected:
        results[case]=recall(args.project,*map(int,case.split('-')),sym,scenes=args.scenes,size=3 if args.size_four else 0)
        (p.OUT/('receipt-'+ '-'.join(selected)+'.json')).write_text(json.dumps(dict(cases=results,
            image_sha256=hashlib.sha256(p.CANDIDATE_IMAGE.read_bytes()).hexdigest(),hardware_tested=False),indent=2)+'\n')


if __name__=='__main__':main()
