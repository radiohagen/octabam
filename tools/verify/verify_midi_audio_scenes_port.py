#!/usr/bin/env python3
"""Run MIDI scene gestures with populated audio SCENES P2 and PLOCKS P2.

Accepts the same --project/--case arguments as the degree-scenes port gate.
Requires a built image carrying SCENES P2, compressed PLOCKS P2 and the
Harmony bridge. Audio playback/editor behavior has its own existing gates;
this checks isolation while MIDI playback, fader, editor and save/resume run.
"""
import json
import sys
import struct
import subprocess
import verify_harmony_degree_scenes_port as scenes

p = scenes.p
CELL = (0x8f3e2 - 0x8ed80) + 15 * 0x100 + 7 * 0x20 + 30
CELL_VALUE = bytes((0x75, 77))
P2_SIZE = 16 * 8 * 768
original_fixture = scenes.fixture
original_run = p.run


def fixture(source, name, *args, **kwargs):
    work = original_fixture(source, name, *args, **kwargs)
    for path in (work / 'project').glob('bank*.work'):
        def seed(data):
            for part in range(8):
                at = p.otp.PART_BASE + part * p.otp.PART_STRIDE + 9 + CELL
                data[at:at+2] = CELL_VALUE
        bank = int(path.stem[4:])
        p.otp._bank_write(work / 'project', bank, seed, guard=False)
        table = b'\xff' * (P2_SIZE-1) + bytes((73,))
        (work / 'project' / f'p2lk{bank:02d}.work').write_bytes(
            struct.pack('>4sIII', b'P2LK', 1, bank-1, P2_SIZE) + table)
    card, _ = p.emu_card.stage_project(work / 'project', 'OCTABAM', 'BASS',
                                      tree=work / 'audio-p2-tree')
    (work / 'card.img').write_bytes(card)
    return work


def run(work, name, extra=(), **kwargs):
    extra = list(extra)
    cell = work / f'{name}-audio-scene.bin'
    lock = work / f'{name}-audio-plock.bin'
    spec = (f'{scenes.PART+CELL:#x},2={cell};'
            f'{symbols["STORE"]+P2_SIZE-1:#x},1={lock}')
    if '--mem-dump' in extra:
        i = extra.index('--mem-dump') + 1
        extra[i] = str(extra[i]) + ';' + spec
    else:
        extra += ['--mem-dump', spec]
    events = original_run(work, name, extra, **kwargs)
    assert cell.read_bytes() == CELL_VALUE, (name, 'audio scene overwritten', cell.read_bytes().hex())
    assert lock.read_bytes() == bytes((73,)), (name, 'audio plock overwritten', lock.read_bytes().hex())
    print(f'[ok] {name}: audio scene and step lock preserved beside MIDI scenes', flush=True)
    return events


if __name__ == '__main__':
    if '--frozen' in sys.argv:
        symbols = json.loads((p.ROOT/'out/degree-scenes-port/candidate-all-symbols.json').read_text())
    else:
        nm = subprocess.check_output(['m68k-elf-nm', str(p.ROOT/'out/platform/runtime/runtime.elf')], text=True)
        symbols = {f[2]: int(f[0], 16) for line in nm.splitlines() if len(f := line.split()) == 3}
    assert all(k in symbols for k in ('STORE', 'hpl_ch_memcpy', 'scn_lib', 'hd_banks'))
    scenes.fixture = fixture
    p.run = run
    scenes.main()
