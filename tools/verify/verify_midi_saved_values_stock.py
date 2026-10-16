#!/usr/bin/env python3
"""Measure Follow/Harmony native SETUP field stock 1.40C compatibility on a disposable virtual card.

Requires the user's firmware and a local project. Publishes no firmware/project
bytes. Exercises the firmware's own load and SAVE PROJECT, not a Python clamp.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import toolpath  # noqa: E402
import ab_fixture  # noqa: E402
import emu_card  # noqa: E402
from hw import ot_project as otp  # noqa: E402

# Native serialized SETUP ranges, distinct from visible encoder ranges.
# Stock accepts 0..127 in disabled NOTE SETUP fields 3/5.
FIELDS = {3: ('RFOL',8,127), 5: ('HARM',2,127),
          12: ('Follow response/mode and Loopback flags',15,0),
          13: ('Follow fixed octave',10,0), 15: ('Follow relative octave biased by 2',4,0),
          16: ('Harmony voicing/spread/root',127,0), 17: ('KEY',84,24),
          18: ('Harmony CHRD/SIZE',31,127), 19: ('Harmony DEG',83,127)}
BANK = 0x400e21e0
STRIDE = 0x9b340
PART = 0x18b2


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--scope', choices=('follow','harmony','harmony-only'), required=True,
                    help='harmony covers the combined Follow/Harmony selection; harmony-only needs no Follow')
    ap.add_argument('--image', type=Path, default=ROOT/'out/mainos_bus.bin',
                    help='explicit immutable candidate when another build may run concurrently')
    args = ap.parse_args()
    selected = (3,12,13,15) if args.scope=='follow' else (5,16,17,18,19) if args.scope=='harmony-only' else tuple(FIELDS)
    fields = {k:v for k,v in FIELDS.items() if k in selected}
    if args.scope == 'harmony-only':
        # The standalone feature uses native Major/Minor; extended KEY modes
        # belong to the separately tested MIDI Scales integration.
        fields[17] = ('KEY', 24, 24)
    out = ROOT / 'out' / ('midi-' + args.scope + '-stock')
    out.mkdir(parents=True, exist_ok=True)
    # Shared verification may rebuild out/ for other remixes. Refuse a wrong
    # candidate before spending time on a disk-load/save run.
    raw_image = args.image.read_bytes()
    counts = {3:0x400d3efc, 5:0x400d3f04, 12:0x400d4082, 13:0x400d4086,
              15:0x400d408e, 16:0x400d4092, 17:0x400d4096,
              18:0x400d43a6, 19:0x400d43aa}
    for field, spec in fields.items():
        offset = counts[field] - 0x40000400
        actual = int.from_bytes(raw_image[offset:offset+4], 'big')
        assert actual == spec[1]+1, ('wrong candidate descriptor',field,actual,spec[1]+1)

    (out / 'receipt.json').unlink(missing_ok=True)
    project = out / 'project'
    ab_fixture.prepare(args.project, project)
    for f in project.glob('project.*'):
        data = re.sub(rb'\[SAMPLE\].*?\[/SAMPLE\]\r?\n', b'', f.read_bytes(), flags=re.S)
        f.write_bytes(data)
    banks = sorted(int(p.stem[4:]) for p in project.glob('bank*.work'))
    assert banks == list(range(1, 17)), 'a complete 16-bank fixture is required'
    def value(bank, part, track):
        if bank == 1:
            return (0, 1, 24, 25, 26, 35, 84, 255)[track]
        return ((bank - 2) * 32 + (part % 4) * 8 + track) % 256
    for bank in banks:
        def seed(data):
            for part in range(8):
                for track in range(8):
                    at = otp.PART_BASE + part * otp.PART_STRIDE + 9 + 0x4e2 + track * 36
                    for field in fields:
                        data[at + field] = value(bank, part, track)
        otp._bank_write(project, bank, seed, guard=False)
    card, _ = emu_card.stage_project(project, 'OCTABAM', 'CHECK', tree=out / 'tree')
    (out / 'seed.img').write_bytes(card)
    # Dismiss a date prompt, open PROJECT, choose SAVE PROJECT and confirm.
    script = ''
    for at, code in [(100, 0x32), (1500, 0x1c), (2500, 0x21),
                     (3200, 0x20), (3900, 0x31), (4600, 0x31)]:
        script += f'{at} key {code:#x} down\n{at + 80} key {code:#x} up\n'
    script += '40000 quit\n'
    (out / 'save.txt').write_text(script)
    candidate = out / 'candidate.bin'
    candidate.write_bytes(raw_image)
    stock = ROOT / 'out/raw/section_3_MAIN_OS.bin'
    runs = []
    for label, image, source, limit in [
        ('candidate', candidate, out / 'seed.img', 1),
        ('stock', stock, out / 'candidate-card.img', 2),
        ('return', candidate, out / 'stock-card.img', 1),
    ]:
        dump = out / (label + '-banks.bin')
        input_files = emu_card.extract_image(source.read_bytes())
        cmd = [str(ROOT / 'out/emu/ot_emu'), '--image', str(image),
               '--card', str(source), '--set', 'OCTABAM', '--project', 'CHECK',
               '--load-ms', '90000', '--mkii', '--live-script', str(out / 'save.txt'),
               '--mem-dump', f'{BANK:#x},{16 * STRIDE}={dump}',
               '--card-out', str(out / (label + '-card.img'))]
        with (out / (label + '.log')).open('w') as log:
            result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        assert result.returncode == 0, (label, result.returncode)
        assert 'ended on quit' in (out / (label + '.log')).read_text(), label
        memory = dump.read_bytes()
        files = emu_card.extract_image((out / (label + '-card.img')).read_bytes())
        checks = 0
        for bank in banks:
            for part in range(4):
                for track in range(8):
                    for field, spec in fields.items():
                        pos = otp.PART_BASE + part * otp.PART_STRIDE + 9 + 0x4e2 + track * 36 + field
                        previous = input_files[f'OCTABAM/CHECK/bank{bank:02d}.work'][pos]
                        expected = min(previous, spec[limit])
                        at = (bank - 1) * STRIDE + 0x8ed80 + part * PART + 0x4e2 + track * 36 + field
                        assert memory[at] == expected, (label, 'RAM', field, bank, part, track, memory[at], expected)
                        for suffix in ('work', 'strd'):
                            data = files[f'OCTABAM/CHECK/bank{bank:02d}.{suffix}']
                            pos = otp.PART_BASE + part * otp.PART_STRIDE + 9 + 0x4e2 + track * 36 + field
                            # SAVE PROJECT writes the current bank. Loading a different
                            # bank's values does not by itself dirty its disk file.
                            disk_expected = expected if bank == 1 else input_files.get(f'OCTABAM/CHECK/bank{bank:02d}.{suffix}', input_files[f'OCTABAM/CHECK/bank{bank:02d}.work'])[pos]
                            assert data[pos] == disk_expected, (label, suffix, bank, part, track, data[pos], disk_expected)
                        checks += 1
        runs.append({'stage': label, 'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
                     'working_part_fields_checked': checks, 'field_maxima': {k:v[limit] for k,v in fields.items()}, 'saved_bank': 1})
        print(f'[ok] {label}: 16 banks x 4 Parts x 8 tracks, RAM, current-bank work/strd save and unchanged other bank files', flush=True)
    receipt = {'status': 'pass', 'fields': fields, 'input_values': 'all bytes 0..255', 'runs': runs,
               'hardware_tested': False,
               'scope': 'SAVE PROJECT writes the current bank; unvisited bank files are unchanged. Cold disk load and native save; retained-memory startup and physical hardware not qualified.'}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
