#!/usr/bin/env python3
"""Compare real native sequencer/ARP/Harmony final UART pitches, OFF versus EXT.

Run in the isolated composed tree carrying the existing Harmony/Follow fixture
tools. Only the disposable project is edited; mapping uses the firmware setter.
"""
import argparse
import hashlib
import json
from pathlib import Path
import verify_midi_harmony_port as p
from verify_midi_loopback_translation import machine


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',type=Path,required=True)
    a=ap.parse_args();p.OUT=p.ROOT/'out/translation-sources'
    image=p.freeze_candidate(p.OUT);sym=machine().sym;cases=[]
    for name,kind,arp,follow in [('normal-transpose',0,False,False),('native-arp',0,True,False),
                               ('harmony',2,False,False),('harmony-arp',2,True,False),
                               ('follow',0,False,True),('follow-arp',0,True,True),
                               ('follow-harmony',2,False,True)]:
        track=1 if follow else 0
        channel=track+1;source=36 if follow else 60
        work=p.fixture(a.project,name,{0:kind,1:kind},arp=arp,tran={0:7})
        extra=['--sequencer','--internal-clock','--frames','7000']
        if follow:
            unfollowed=p.run(work,'unfollowed',extra)
            extra+=['--step','-:poke:0x100b14cc=1','--step',f'-:call:{sym["bf_encoder"]:#x},3,4']
        off=p.run(work,'off',extra);p.balanced(off)
        if follow:
            assert [e for e in off if e[1]==channel]!=[e for e in unfollowed if e[1]==channel], 'Follow did not alter generated notes'
        on=p.run(work,'translated',[*extra,
            '--step',f'-:call:{sym["lt_set"]:#x},0,{track},1,{source}',
            '--step',f'-:call:{sym["lt_set"]:#x},0,{track},0,2'])
        p.balanced(on)
        want=[]
        for event in off:
            event=list(event)
            if event[1]==channel:
                event[2]+=84-source
                if not 72<=event[2]<=96:continue
            want.append(tuple(event))
        assert on==want,(name,on,want)
        pitches=sorted({e[2] for e in off if e[0]=='on' and e[1]==channel})
        assert pitches and any(e[0]=='on' and e[1]==channel for e in on),name
        assert any(pitch!=60 for pitch in pitches),'fixture did not generate final pitches'
        cases.append(dict(name=name,raw_final_pitches=pitches,note_events=len(on)))
        print('[ok]',name,'final pitches',pitches,'-> mapped UART events',len(on),flush=True)
    (p.OUT/'result.json').write_text(json.dumps(dict(status='PASS',cases=cases,
        image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),hardware_tested=False),indent=2)+'\n')


if __name__=='__main__':main()
