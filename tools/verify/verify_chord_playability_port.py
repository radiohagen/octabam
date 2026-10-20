#!/usr/bin/env python3
"""Actual-panel/UART acceptance for silent releases and the Part-owned spacing controls."""
import argparse
import json
import subprocess
import verify_chord_play_port as c
import verify_midi_harmony_port as p


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',required=True,type=c.Path);ap.add_argument('--reuse-candidate',action='store_true')
    args=ap.parse_args()
    out=p.ROOT/'out/chord-playability-port';p.OUT=out;c.OUT=out
    if args.reuse_candidate:
        p.CANDIDATE_IMAGE=out/'candidate.bin'
        frozen=json.loads((out/'candidate-symbols.json').read_text())
        p.harmony.symbols=lambda:frozen
    else:p.freeze_candidate(out)
    c.SYMBOLS=p.harmony.symbols();sym=c.SYMBOLS
    original_dump=c.dump
    c.dump=lambda work,name:original_dump(work,name)+f';0x100a4ece,6322={work}/{name}-part.bin'

    results={}
    # Both release orders, an idle gap between MAJ and DOM7, and the new-root reset.
    for arp in (False,True):
        work=p.fixture(args.project,f'release-arp-{int(arp)}',{0:2},key_raw=2,arp=arp)
        script=c.PANEL+'''1600 key 4 down
2200 key 13 down
2800 key 13 up
3400 key 15 down
4000 key 15 up
4600 key 4 up
5200 key 4 down
5800 key 13 down
6400 key 4 up
7000 key 13 up
7600 key 4 down
8200 key 4 up
8700 quit
'''
        events=c.run(work,'release',script)
        notes=[e[2] for e in events if e[:2]==('on',1)]
        if not arp:
            want=[55,58,62,55,59,62,55,59,62,65,55,58,62,55,59,62,55,58,62]
            assert notes==want,(notes,want)
        else:
            # The arp keeps ticking, so linked dispatch proves the absence of
            # release-triggered key calls; here assert captured ownership drains.
            assert notes and set(notes)<={55,58,59,62,65},notes
        results[work.name]=notes
        print(f'[ok] {work.name}: MAJ release gap, DOM7, both release orders, next-root reset and balanced MIDI',flush=True)
    # Leave G SUS4 sounding after a newer F TRI is released. The guide
    # must read G's captured quality, not the current base used for F.
    work=p.fixture(args.project,'overlap-guide',{0:2},key_raw=2)
    script=work/'overlap.txt'
    script.write_text(c.PANEL+'1600 key 4 down\n2000 key 12 down\n2400 key 12 up\n2800 key 3 down\n3300 key 3 up\n3800 quit\n')
    p.run(work,'overlap',['--live-script',script,'--lcd',work/'overlap.lcd',
          '--mem-dump',f'{sym["ch_display_root"]:#x},2={work}/identity.bin'])
    assert (work/'identity.bin').read_bytes()==bytes((55,4))
    subprocess.run([p.sys.executable,str(p.ROOT/'tools/emu/lcd_view.py'),str(work/'overlap.lcd'),'--png',str(work/'overlap.png')],check=True,stdout=subprocess.DEVNULL)
    results['overlap-guide']={'root':55,'quality':4,'intentionally_held_at_capture':True}
    print('[ok] overlapping roots: G SUS4 guide retains its captured quality after F TRI releases',flush=True)
    for spread in range(3):
        name=f'auto-spread-{spread}'
        work=p.fixture(args.project,name,{0:2},auto=(0,),spreads={0:spread})
        setup=c.PANEL+'''1500 key 0x2d down
1600 key 0x22 down
1700 key 0x22 up
1800 key 0x2d up
2000 key 0x3d down
2050 key 0x3d up
'''

        c.run(work,'baseline',setup+'2100 quit\n')
        setup+='2200 enc 4 4\n2300 enc 5 4\n'
        c.run(work,'page',setup+'2500 quit\n')
        assert (work/'page-part.bin').read_bytes()==(work/'baseline-part.bin').read_bytes(), 'Inactive E/F changed native Part'
        subprocess.run([p.sys.executable,str(p.ROOT/'tools/emu/lcd_view.py'),str(work/'page.lcd'),'--png',str(work/'page.png')],check=True,stdout=subprocess.DEVNULL)
        script=setup+'''2500 key 0x32 down
2550 key 0x32 up
2700 key 0x32 down
2750 key 0x32 up
'''

        keys=(0,3,4,0,4,3,0,7,0,0)
        for i,key in enumerate(keys):
            at=3200+i*600;script+=f'{at} key {key} down\n{at+350} key {key} up\n'
        script+='9600 quit\n'
        events=c.run(work,'play',script)
        pitches=[e[2] for e in events if e[:2]==('on',1)]
        assert len(pitches)==len(keys)*3,(name,pitches)
        chords=[pitches[i:i+3] for i in range(0,len(pitches),3)]
        roots=[48,53,55,48,55,53,48,60,48,48]
        assert all(root in chord for root,chord in zip(roots,chords)),(name,chords)
        assert chords[-1]==chords[-2],(name,chords)
        assert chords[0]==([48,52,55],[48,55,64],[48,64,67])[spread],chords
        results[name]=chords
        print(f'[ok] {name}: inactive E/F, SPRD spacing, anchored roots, repeated roots, octave return and balanced MIDI',flush=True)
    (out/'receipt.json').write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':main()
