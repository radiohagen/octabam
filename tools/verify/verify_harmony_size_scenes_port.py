#!/usr/bin/env python3
"""Fixed SIZE across MIDI scene endpoints beside audio page-2 scene/step locks."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import verify_midi_audio_scenes_port as audio

p = audio.p


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', required=True, type=Path)
    args = ap.parse_args()
    p.OUT = p.ROOT / 'out/harmony-size-scenes-port'
    p.freeze_candidate(p.OUT)
    raw = subprocess.check_output(['m68k-elf-nm', str(p.ROOT/'out/platform/runtime/runtime.elf')], text=True)
    sym = {f[2]: int(f[0], 16) for line in raw.splitlines() if len(f := line.split()) == 3}
    assert all(k in sym for k in ('STORE', 'hpl_ch_memcpy', 'scn_lib', 'mh_refs'))
    audio.symbols = sym
    results = {}
    for size in (2, 3, 4):
        for xf, triad in ((0, [55, 58, 62]), (127, [48, 51, 55])):
            want = triad[:2] if size == 2 else triad + ([triad[0]+12] if size == 4 else [])
            for arp in (False, True):
                name = f'size{size}-xf{xf}-arp{int(arp)}'
                work = audio.fixture(args.project, name, arp=arp)
                for path in (work/'project').glob('bank*.work'):
                    def seed(data):
                        for part in range(8):
                            base = p.otp.PART_BASE + part*p.otp.PART_STRIDE + 9
                            for track in range(8):
                                at = base + 0x4e2 + 36*track + 18
                                data[at] = (data[at] & 7) | ((size-1) << 3)
                                if arp:
                                    data[base + 0x3e2 + 32*track + 15] = 1
                    p.otp._bank_write(work/'project', int(path.stem[4:]), seed, guard=False)
                card, _ = p.emu_card.stage_project(work/'project', 'OCTABAM', 'BASS', tree=work/'size-tree')
                (work/'card.img').write_bytes(card)
                events = audio.run(work, 'play', ['--sequencer', '--internal-clock', '--frames', '7000',
                    '--step', f'-:poke:0x460d16c8=0;0x460d16c9=0;0x460d16ca=0;0x460d16cb={xf}',
                    '--mem-dump', f'{sym["mh_refs"]:#x},1024={work}/refs.bin'])
                p.balanced(events)
                notes = [e[2] for e in events if e[:2] == ('on', 1)]
                assert (set(notes) == set(want) if arp else notes == want*3), (name, notes, want)
                assert (work/'refs.bin').read_bytes() == bytes(1024), name
                results[name] = dict(notes=notes, expected=want, held_owners_after_stop=0,
                                     audio_scene_and_step_lock_preserved=True)
                (p.OUT/'receipt.json').write_text(json.dumps(dict(cases=results,
                    image_sha256=hashlib.sha256(p.CANDIDATE_IMAGE.read_bytes()).hexdigest(),
                    hardware_tested=False), indent=2)+'\n')
                print('[ok]', name, want, flush=True)


if __name__ == '__main__':
    main()
