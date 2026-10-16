#!/usr/bin/env python3
"""Degree scenes on the full firmware and a disposable virtual CF card."""
import argparse
import hashlib
import json
import subprocess
import struct
import zlib
from pathlib import Path
import verify_midi_harmony_port as p
import verify_chord_play_port as cp

def write_scene_file(project, tables):
    payload=bytearray(b'\xff'*(64*4096))
    for context,entries in tables.items():
        for index,value in entries:payload[context*4096+index]=value
    data=struct.pack('>4sIII',b'MSCW',1,len(payload),zlib.crc32(payload))+payload
    for suffix in ('work','strd'):(project/f'scenes.{suffix}').write_bytes(data)


B=0x400e21e0
PART=B+0x8ed80


def fixture(source,name,mode=2,key=2,arp=False):
    w=p.fixture(source,name,{0:mode},key_raw=key,first_note=48,arp=arp)
    for path in (w/'project').glob('bank*.work'):
        def seed(data):
            for part in range(8):
                base=p.otp.PART_BASE+part*p.otp.PART_STRIDE+9
                data[base+0x10:base+0x12]=bytes((0,1))
                for track in range(8):data[base+0x4e2+36*track+19]=35
        p.otp._bank_write(w/'project',int(path.stem[4:]),seed,guard=False)
    endpoints=(35,39) if mode else (48,55)
    write_scene_file(w/'project',{c:[(0,endpoints[0]),(256,endpoints[1])] for c in range(64)})
    card,_=p.emu_card.stage_project(w/'project','OCTABAM','BASS',tree=w/'scene-tree')
    (w/'card.img').write_bytes(card)
    return w


def playback(source,sym):
    results={}
    for mode,key,xf,want in ((1,2,0,[55]*3),(2,2,0,[55,58,62]*3),(2,6,0,[57,60,64]*3),(2,2,127,[48,51,55]*3),(0,2,0,[55,55,58,55])):
        name=f'mode{mode}-key{key}-xf{xf}'
        w=fixture(source,name,mode,key)
        events=p.run(w,'play',['--sequencer','--internal-clock','--frames','7000',
            '--step',f'-:poke:0x460d16c8={xf>>24};0x460d16c9=0;0x460d16ca=0;0x460d16cb={xf}',
            '--mem-dump',f'{PART:#x},0x18b2={w}/part.bin;{sym["mh_refs"]:#x},1024={w}/refs.bin'])
        p.balanced(events)
        notes=[e[2] for e in events if e[:2]==('on',1)]
        assert notes==want,(name,notes,want)
        assert (w/'refs.bin').read_bytes()==bytes(1024)
        results[name]=notes
        print(f'[ok] {name}: scene root, chord and balanced release',flush=True)
    return results


def editor(source,sym):
    w=fixture(source,'scene-editor')
    script=w/'edit.txt'
    script.write_text('100 key 0x31 down\n150 key 0x31 up\n500 key 0x22 down\n550 key 0x22 up\n1000 key 0x19 down\n1600 enc 0 1\n2000 key 0x19 up\n2600 quit\n')
    extra=['--step','-:poke:0x80000015=1;0x460d16f3=1;0x100b14cc=0',
           '--internal-clock','--live-script',script,'--lcd',w/'edit.lcd',
           '--mem-dump',f'{B:#x},0x9b340={w}/bank.bin;0x10000000,0x100000={w}/cs1.bin;{sym["scn_lib"]:#x},4096={w}/scenes.bin']
    events=p.run(w,'edit',extra,physical_panel=True);p.balanced(events)
    bank=(w/'bank.bin').read_bytes()
    table=(w/'scenes.bin').read_bytes()
    assert table[0]==36 and table[256]==39,(table[0],table[256])
    assert bank[0x8ed80+0x4e2+19]==35
    # FUNC + the same physical Scene encoder advances only the tonic octave.
    octave=w/'octave.txt'
    octave.write_text(script.read_text().replace('1600 enc 0 1',
        '1300 key 0x2d down\n1600 enc 0 1\n1800 key 0x2d up'))
    options=list(extra);options[options.index('--live-script')+1]=octave
    events=p.run(w,'octave',options,physical_panel=True);p.balanced(events)
    octave_bank=(w/'bank.bin').read_bytes()
    assert (w/'scenes.bin').read_bytes()[0]==42
    # Physical SAVE, cold reload and retained resume use native scene storage.
    script.write_text(script.read_text().replace('2600 quit\n','')+cp.SAVE)
    events=p.run(w,'save',extra,physical_panel=True);p.balanced(events)
    for name,options in [('cold',()),('warm',('--no-post','--cs1-in',w/'cs1.bin'))]:
        events=p.run(w,name,['--sequencer','--internal-clock','--frames','7000',
             '--step','-:poke:0x460d16cb=127',*options,
             '--mem-dump',f'{PART:#x},0x18b2={w}/{name}-part.bin;{sym["scn_lib"]:#x},4096={w}/{name}-scenes.bin'],card=w/'save-card.img')
        p.balanced(events)
        notes=[e[2] for e in events if e[:2]==('on',1)]
        assert notes==[50,53,56]*3,(name,notes)
        table=(w/f'{name}-scenes.bin').read_bytes()
        assert table[0]==36 and table[256]==39
    print('[ok] physical scene encoder, project SAVE, cold reload and retained resume',flush=True)
    return {'edited_degree':36,'part_degree_unchanged':35,'cold_and_retained_notes':[50,53,56]*3}


def stress(source,sym):
    results={}
    for arp in (False,True):
        w=fixture(source,'all-track-arp' if arp else 'all-track-chords',arp=arp)
        for path in (w/'project').glob('bank*.work'):
            def seed(data):
                for part in range(8):
                    base=p.otp.PART_BASE+part*p.otp.PART_STRIDE+9
                    entries=[]
                    for track in range(8):
                        at=base+0x4e2+36*track
                        data[at]=track+1 if arp else 1  # shared chords; distinct native arp destinations
                        data[at+3]=0;data[at+5]=2;data[at+17]=2
                        if arp:
                            param=base+0x3e2+track*32
                            data[param+2]=18;data[param+14]=1;data[param+15]=3
                        entries.extend(((track*32,35),(256+track*32,42)))
                lane=bytes(data[0x492e:0x492e+0x8b9])
                for track in range(1,8):data[0x492e+track*0x8b9+9:0x492e+(track+1)*0x8b9]=lane[9:]
            p.otp._bank_write(w/'project',int(path.stem[4:]),seed,guard=False)
        write_scene_file(w/'project',{c:[(scene*256+t*32,35 if scene==0 else 42) for scene in (0,1) for t in range(8)] for c in range(64)})
        card,_=p.emu_card.stage_project(w/'project','OCTABAM','BASS',tree=w/'stress-tree')
        (w/'card.img').write_bytes(card)
        script=w/'sweep.txt'
        script.write_text('100 key 0x31 down\n150 key 0x31 up\n300 pot 255\n500 key 0x28 down\n550 key 0x28 up\n1000 pot 0\n1500 pot 128\n2000 pot 255\n2500 pot 0\n3000 pot 255\n5000 key 0x27 down\n5050 key 0x27 up\n6500 quit\n')
        events=p.run(w,'sweep',['--internal-clock','--live-script',script,
            '--mem-dump',f'{sym["mh_refs"]:#x},1024={w}/refs.bin;0x460d16c8,4={w}/xf.bin'])
        p.balanced(events)
        notes=[e[2] for e in events if e[0]=='on']
        assert len(notes)>=9 and all(n%12 in (0,2,3,5,7,8,10) for n in notes),notes
        assert len(set(notes))>=4,notes
        assert (w/'refs.bin').read_bytes()==bytes(1024)
        results['arp' if arp else 'chords']={'note_ons':len(notes),'pitches':sorted(set(notes)),'held_owners_after_stop':0}
        print(f'[ok] eight tracks, physical fader, arp={arp}: releases drained',flush=True)
    return results


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',required=True,type=Path)
    ap.add_argument('--frozen',action='store_true')
    ap.add_argument('--case',choices=('playback','editor','stress'),action='append')
    args=ap.parse_args()
    p.OUT=p.ROOT/'out/degree-scenes-port'
    if args.frozen:
        p.CANDIDATE_IMAGE=p.OUT/'candidate.bin'
        sym=json.loads((p.OUT/'candidate-all-symbols.json').read_text())
    else:
        raw=subprocess.check_output(['m68k-elf-nm',str(p.ROOT/'out/platform/runtime/runtime.elf')],text=True)
        sym={f[2]:int(f[0],16) for line in raw.splitlines() if len(f:=line.split())==3}
        assert all(k in sym for k in ('KIMG','scn_lib','hd_banks'))
        p.freeze_candidate(p.OUT)
        (p.OUT/'candidate-all-symbols.json').write_text(json.dumps(sym,indent=2)+'\n')
    p.harmony.symbols=lambda:sym
    results={}
    selected=args.case or ('playback','editor','stress')
    for case in args.case or ('playback','editor','stress'):
        results[case]={'playback':playback,'editor':editor,'stress':stress}[case](args.project,sym)
    (p.OUT/('receipt-'+ '-'.join(selected)+'.json')).write_text(json.dumps(dict(cases=results,
        image_sha256=hashlib.sha256(p.CANDIDATE_IMAGE.read_bytes()).hexdigest(),hardware_tested=False),indent=2)+'\n')


if __name__=='__main__':main()
