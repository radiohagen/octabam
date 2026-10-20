#!/usr/bin/env python3
"""SIZE through the stock sequencer/arp and physical CHORD PLAY on virtual CF."""
import argparse
import hashlib
import json
from pathlib import Path
import verify_midi_harmony_port as p
import verify_chord_play_port as cp


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',required=True,type=Path)
    ap.add_argument('--case',action='append',choices=('sequence','live','follow','persistence','musical','live-drop'))
    args=ap.parse_args()
    p.OUT=p.ROOT/'out/harmony-size-port';p.freeze_candidate(p.OUT)
    sym=p.harmony.symbols();results={}
    expected={1:[[48,52],[48,59],[48,62]],
              2:[[48,52,55],[48,52,59],[48,52,62]],
              3:[[48,52,55,60],[48,52,55,59],[48,52,55,62]]}
    for size in ((1,2,3) if not args.case or 'sequence' in args.case else ()):
        for arp in (False,True):
            name=f'size{size+1}-'+('arp' if arp else 'sequence')
            work=p.fixture(args.project,name,{0:2},arp=arp,sizes={0:size},first_note=48)
            for path in (work/'project').glob('bank*.work'):
                def seed(data):
                    for step in (2,4,8):data[0x492e+0x39+step*32]=48
                    if arp:
                        # Four notes must fit before the next chord trigger.
                        for part in range(8):
                            base=p.otp.PART_BASE+part*p.otp.PART_STRIDE+9
                            data[base+0x3e2+15]=1
                p.otp._bank_write(work/'project',int(path.stem[4:]),seed,guard=False)
            card,_=p.emu_card.stage_project(work/'project','OCTABAM','BASS',tree=work/'size-tree')
            (work/'card.img').write_bytes(card)
            events=p.run(work,'play',['--step',f'-:poke:{sym["ch_lock_table"]+2:#x}=0;{sym["ch_lock_table"]+4:#x}=1;{sym["ch_lock_table"]+8:#x}=2',
                '--sequencer','--internal-clock','--frames','7000',
                '--mem-dump',f'{sym["mh_refs"]:#x},1024={work}/refs.bin'])
            p.balanced(events)
            notes=[e[2] for e in events if e[:2]==('on',1)]
            if arp:
                assert set(notes)==set(sum(expected[size],[])),(name,notes)
            else:assert notes==sum(expected[size],[]),(name,notes)
            assert (work/'refs.bin').read_bytes()==bytes(1024)
            results[name]=notes
            print('[ok]',name,notes,flush=True)
    # Physical variation keys retrigger a held root while AUTO spans quality
    # changes; releasing keys must drain the original generated voices.
    for size in ((1,2,3) if not args.case or 'live' in args.case else ()):
        name=f'size{size+1}-live-auto'
        work=p.fixture(args.project,name,{0:2},key_raw=1,sizes={0:size},auto=(0,))
        script=work/'live.txt'
        script.write_text(cp.PANEL+'1600 key 0 down\n2200 key 9 down\n2800 key 9 up\n3400 key 0 up\n4000 quit\n')
        events=p.run(work,'live',['--live-script',script,'--mem-dump',f'{sym["mh_refs"]:#x},1024={work}/refs.bin'])
        p.balanced(events)
        notes=[e[2] for e in events if e[:2]==('on',1)]
        # Common notes are released/retriggered by CHORD PLAY's established
        # variation gesture; this gate pins final pools, not legato allocation.
        want=expected[size][0]+expected[size][1]
        assert notes==want,(name,notes)
        assert (work/'refs.bin').read_bytes()==bytes(1024)
        results[name]=notes
        print('[ok]',name,notes,flush=True)
    if 'bf_source_get' in sym and (not args.case or 'follow' in args.case):
        work=p.fixture(args.project,'follow',{0:2,1:3},sizes={0:3,1:1},auto=(0,1))
        events=p.run(work,'play',['--step','-:poke:0x100b14cc=1',
            '--step',f'-:call:{sym["bf_encoder"]:#x},3,4',
            '--sequencer','--internal-clock','--frames','7000'])
        p.balanced(events)
        receiver=[e[2] for e in events if e[:2]==('on',2)]
        assert receiver==[47,57,38,48,38,48,41,52,43,53,43,53],receiver
        results['follow']=receiver
        print('[ok] Follow inherits root/scale and keeps receiver SIZE 2 against SIZE 4 leader',flush=True)
    if not args.case or 'persistence' in args.case:
        results['persistence']=p.persistence(args.project)
    if not args.case or 'musical' in args.case:
        examples=[
            ('low-size2',1,0,[48,48,48],[0,1,2],[[48,52],[48,59],[48,62]]),
            ('bass-size4',3,2,[60,60,60],[0,1,2],[[48,60,64,67],[48,59,64,67],[48,62,64,67]]),
            ('rootless-add9',2,1,[60,65,67],[2,2,2],[[64,67,74],[60,67,69],[59,62,69]]),
        ]
        for name,size,root_mode,pitches,qualities,want in examples:
            work=p.fixture(args.project,name,{0:2},sizes={0:size},roots={0:root_mode},auto=(0,),first_note=pitches[0])
            for path in (work/'project').glob('bank*.work'):
                def seed(data):
                    for step,note in zip((2,4,8),pitches):data[0x492e+0x39+step*32]=note
                p.otp._bank_write(work/'project',int(path.stem[4:]),seed,guard=False)
            card,_=p.emu_card.stage_project(work/'project','OCTABAM','BASS',tree=work/'musical-tree')
            (work/'card.img').write_bytes(card)
            locks=';'.join(f'{sym["ch_lock_table"]+step:#x}={q}' for step,q in zip((2,4,8),qualities))
            events=p.run(work,'play',['--step','-:poke:'+locks,'--sequencer','--internal-clock','--frames','7000',
                '--mem-dump',f'{sym["mh_refs"]:#x},1024={work}/refs.bin'])
            p.balanced(events)
            notes=[e[2] for e in events if e[:2]==('on',1)]
            assert notes==sum(want,[]),(name,notes,want)
            assert (work/'refs.bin').read_bytes()==bytes(1024)
            results[name]=notes
            print('[ok] native musical outcome',name,notes,flush=True)
    if not args.case or 'live-drop' in args.case:
        work=p.fixture(args.project,'live-drop',{0:2},sizes={0:3},roots={0:2},auto=(0,))
        script=work/'live.txt'
        script.write_text(cp.PANEL+'1600 key 0 down\n2200 key 9 down\n2800 key 9 up\n3400 key 0 up\n4000 quit\n')
        events=p.run(work,'live',['--live-script',script,'--mem-dump',f'{sym["mh_refs"]:#x},1024={work}/refs.bin'])
        p.balanced(events)
        notes=[e[2] for e in events if e[:2]==('on',1)]
        assert notes==[36,48,52,55,36,47,52,55],notes
        assert (work/'refs.bin').read_bytes()==bytes(1024)
        results['live-drop']=notes
        print('[ok] held dropped-root triad: doubled input root becomes the seventh and all releases drain',flush=True)
    (p.OUT/('receipt-'+ '-'.join(args.case)+'.json' if args.case else 'receipt.json')).write_text(json.dumps(dict(cases=results,
        image_sha256=hashlib.sha256(p.CANDIDATE_IMAGE.read_bytes()).hexdigest(),
        hardware_tested=False),indent=2)+'\n')


if __name__=='__main__':main()
