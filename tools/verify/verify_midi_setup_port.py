#!/usr/bin/env python3
"""Physical NOTE SETUP confirmation: live module values and stock staged edits."""
import argparse
import hashlib
import json
from pathlib import Path
import verify_midi_harmony_port as p
import verify_chord_play_port as panel

OUT = p.ROOT/'out/midi-setup-port'
PART = 0x400e21e0+0x8ed80


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    p.OUT = OUT
    p.freeze_candidate(OUT)
    symbols = p.harmony.symbols()
    assert 'mh_set' in symbols and 'bf_select' in symbols, 'select Harmony and Follow'
    work = p.fixture(args.project, 'confirm', {0:0}, key_raw=2)
    setup = panel.key(100,0x31)+panel.key(600,0x35)+panel.key(1100,0x10)
    setup += ('1600 key 0x2d down\n1700 key 0x22 down\n'
              '1850 key 0x22 up\n1950 key 0x2d up\n')
    edits = '2300 enc 3 4\n2500 enc 5 4\n'
    cases = {
        'live': setup+edits+'2900 quit\n',
        'yes': setup+edits+panel.key(3000,0x31)+'3500 quit\n',
        'mixed': setup+edits+'2700 enc 0 4\n'+panel.key(3000,0x31)+panel.key(3400,0x31)+'3900 quit\n',
        'off': setup+edits+'2700 enc 5 -4\n'+panel.key(3000,0x31)+'3500 quit\n',
        # Modal editors close with YES, then NOTE SETUP YES must keep both.
        'windows': setup+panel.key(2200,0x3b)+'2500 enc 0 4\n'+panel.key(2800,0x31)
                   +panel.key(3200,0x3d)+'3500 enc 0 4\n'+panel.key(3800,0x31)
                   +panel.key(4200,0x31)+'4700 quit\n',
    }
    results = {}
    for name,script in cases.items():
        path=work/f'{name}.txt';path.write_text(script)
        p.run(work,name,['--live-script',path,'--mem-dump',
              f'{PART:#x},6322={work}/{name}-part.bin;0x10000000,0x100000={work}/{name}-cs1.bin'],physical_panel=True)
        part=(work/f'{name}-part.bin').read_bytes()
        actual=(part[0x4e2+3],part[0x4e2+5])
        expected=(2,0 if name=='off' else 1)
        assert actual==expected,(name,actual,expected)
        if name=='live':baseline=part
        elif name=='mixed':
            assert part[0x4e2]!=baseline[0x4e2], 'YES must still commit stock CHAN'
            assert part[0x4e2+1:0x4e2+6]==baseline[0x4e2+1:0x4e2+6]
        elif name in ('yes','windows'):
            assert part[0x4e2:0x4e2+6]==baseline[0x4e2:0x4e2+6]
        results[name]=list(actual)
        print('[ok]',name,'RFOL/HARM',actual,flush=True)
    (OUT/'receipt.json').write_text(json.dumps(dict(cases=results,
        image_sha256=hashlib.sha256(p.CANDIDATE_IMAGE.read_bytes()).hexdigest(),
        hardware_tested=False),indent=2)+'\n')


if __name__=='__main__':
    main()
