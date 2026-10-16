#!/usr/bin/env python3
"""Native Part mode/default transitions through the full firmware, without KITS."""
import argparse
import hashlib
import json
from pathlib import Path
import verify_midi_harmony_port as p

B=0x400e21e0
PS=0x18b2


def transition(source, outgoing, incoming, symbols):
    name=f'{outgoing}-to-{incoming}'
    work=p.fixture(source,name,{0:outgoing},key_raw=2,first_note=48)
    for path in (work/'project').glob('bank*.work'):
        def seed(data):
            for part in range(8):
                base=p.otp.PART_BASE+part*p.otp.PART_STRIDE+9
                for track in range(8):
                    at=base+0x4e2+track*36
                    data[at+19]=35
                # Native saved/working Part 1: the incoming defaults are
                # deliberately different from the outgoing explicit tonic.
                if part%4==1:
                    at=base+0x4e2
                    data[at+5]=incoming
                    data[at+17]=6
                    data[at+18]=1
                    data[at+19]=39
                    data[base+0x3e2]=65
            at=0x492e+0x39
            data[at+2*32]=49 if outgoing==0 else 48
            for step in (4,8):data[at+step*32]=255
            for step in (2,4,8):data[at+step*32+3:at+step*32+6]=b'\xff'*3
        p.otp._bank_write(work/'project',int(path.stem[4:]),seed,guard=False)
    card,_=p.emu_card.stage_project(work/'project','OCTABAM','BASS',tree=work/'seed-tree')
    (work/'card.img').write_bytes(card)
    steps=['--step',f'-:call:{symbols["hd_sync_c"]:#x},0,0,0']
    if outgoing:
        steps+=['--step',f'-:call:{symbols["hd_edit_step_c"]:#x},0,0,0,2,35']
    steps+=['--step',f'-:dump:{B:#x},0x9b340={work}/before.bin',
            '--step','-:call:0x4004a8a4,1',
            '--sequencer','--internal-clock','--frames','7000',
            '--mem-dump',f'{B:#x},0x9b340={work}/after.bin;'
                         f'{symbols["hd_banks"]:#x},16768={work}/roots.bin;'
                         f'0x80001828,18={work}/engine.bin']
    events=p.run(work,'play',steps)
    p.balanced(events)
    notes=[e[2] for e in events if e[:2]==('on',1)]
    root=50 if outgoing else 48
    # OFF retains native KEY quantization: the stored C# stays C# while
    # stock D-minor KEY emits C. This is not a degree conversion.
    expected=([48,65,65] if incoming==0 else
              [root,57,57] if incoming==1 else
              ([50,53,57,60] if outgoing else [48,52,55,58])+[57,60,64,67]*2)
    assert notes==expected,(name,notes,expected)
    before=(work/'before.bin').read_bytes();after=(work/'after.bin').read_bytes()
    # A recall never converts incoming defaults or changes another Part.
    assert before[0x8ed80:0x95048]==after[0x8ed80:0x95048],name
    assert after[0x8e57]==1
    assert after[0x4900+2*32]==(47 if incoming and not outgoing else 48 if outgoing else 49)  # canonical HARM mirror
    assert after[0x4900+4*32]==after[0x4900+8*32]==255
    roots=(work/'roots.bin').read_bytes()
    assert roots[2]==((35 if outgoing else 34) if incoming else 255)
    assert roots[4]==roots[8]==255
    print(f'[ok] native Part {name}: explicit root {notes[0]}, incoming defaults, balanced releases',flush=True)
    return {'notes':notes,'incoming_defaults_unchanged':True,'explicit_and_unlocked_separate':True}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',type=Path,required=True)
    ap.add_argument('--case',action='append',choices=[f'{a}-{b}' for a in range(3) for b in range(3)])
    args=ap.parse_args()
    p.OUT=p.ROOT/'out/degree-native-part-port';p.OUT.mkdir(parents=True,exist_ok=True)
    p.freeze_candidate(p.OUT);symbols=p.harmony.symbols()
    selected=args.case or [f'{a}-{b}' for a in range(3) for b in range(3)]
    result={}
    for case in selected:
        result[case]=transition(args.project,*map(int,case.split('-')),symbols)
        (p.OUT/'receipt.json').write_text(json.dumps({'cases':result,
            'image_sha256':hashlib.sha256(p.CANDIDATE_IMAGE.read_bytes()).hexdigest(),
            'hardware_tested':False},indent=2)+'\n')


if __name__=='__main__':main()
