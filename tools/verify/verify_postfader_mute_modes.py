#!/usr/bin/env python3
"""Installed MUTE_MODES OT-exit + POST FADER integration; no DSP/audio render.

Run the actual stock mixer publisher, its installed MUTE_MODES detour, and
the installed POST FADER detour. Inputs to the publisher and FX records are
seeded. The record builder and note-off callback are intercepted, so this
isolates frame gain integration; it cannot qualify alternate-mode audio tails.

The fixture is specific to test/send-return-poc: BusDelay on T1, BusVerb on
T5, SEND on T2-T4/T6-T7, and RETURNS on T8. Each source track and both ping
banks exercise OT unmuted -> OT muted -> alternate mode while held -> one
more held frame -> unmute -> remute. In an already-active alternate mode,
remuting intentionally leaves MAIN/send coefficients open: the mode's own
voice release, trig suppression or pre-insert dry cut supplies the mute.

A final negative control bypasses p1_hold only in emulator memory and
requires the held transition to fail. Image files and author code are unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import toolpath  # noqa: E402,F401
from image_dsp import unpack_payload
from remix import registry
from remix.platform_build import UNCACHED
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn import m68k_const as R

BASE, STACK, STOP = 0x40000400, 0x40fff000, 0x40fff100
PUBLISH, MM_HOOK = 0x40004db8, 0x40004dc6
PF_HOOK, PF_END, BUILDER, NOTEOFF = 0x4000d0e4, 0x4000d0ea, 0x40004bd4, 0x40008f84
RECORDS, MIX = 0x80000110, 0x80006000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('remix')
    ap.add_argument('--image', type=Path, default=ROOT / 'out/mainos_bus.bin')
    ap.add_argument('--elf', type=Path, default=ROOT / 'out/platform/runtime/runtime.elf')
    ap.add_argument('--layout', type=Path, default=ROOT / 'out/platform/layout.json')
    ap.add_argument('--receipt', type=Path)
    args = ap.parse_args()
    remix = registry.remix(args.remix)
    if 'MUTE_MODES' not in remix.modules:
        print('[ -- ] no MUTE_MODES; no integration cases run')
        return
    if args.remix != 'test/send-return-poc':
        ap.error('this fixture supports only test/send-return-poc with its T1/T5/T8 layout')
    if not {'POST FADER', 'RETURNS', 'RIG HOSTS', 'DELAY SERVER', 'REVERB SERVER', 'SEND'} <= set(remix.modules):
        ap.error('the selected remix no longer has the required T1/T5/T8 bus modules')
    if 'SIDECHAIN_COMPRESSOR' in remix.modules:
        ap.error('this fixture covers the plain MUTE_MODES unit, without SIDECHAIN_COMPRESSOR')
    image = args.image.read_bytes()
    layout = json.loads(args.layout.read_text())
    runtime = unpack_payload(image, layout['base'] + UNCACHED)
    assert layout['runtime_end'] == layout['base'] + len(runtime)
    nm = subprocess.check_output(['m68k-elf-nm', str(args.elf)], text=True)
    symbols = {p[2]: int(p[0], 16) for line in nm.splitlines()
               if len(p := line.split()) == 3 and
               layout['base'] <= int(p[0], 16) < layout['runtime_end']}
    assert image[MM_HOOK - BASE:MM_HOOK - BASE + 6] == b'\x4e\xf9' + symbols['pre'].to_bytes(4, 'big')
    assert image[PF_HOOK - BASE:PF_END - BASE] == b'\x4e\xb9' + symbols['pf_frame'].to_bytes(4, 'big')
    assert symbols['SHADOW'] == symbols['UNHELD'] + 1
    mods = registry.bound(remix)
    ids = {key: mods[key].menu.fx2_id for key in ('SEND', 'DELAY SERVER', 'REVERB SERVER', 'RETURNS')}
    effects = [ids['DELAY SERVER']] + [ids['SEND']] * 3 + [ids['REVERB SERVER']] + [ids['SEND']] * 2 + [ids['RETURNS']]
    checks = 0
    sequences = []

    def check(condition, label):
        nonlocal checks
        checks += 1
        assert condition, label

    def new_machine():
        uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        uc.ctl_set_cpu_model(R.UC_CPU_M68K_CFV4E)
        uc.mem_map(0x40000000, 0x1000000)
        uc.mem_map(0x80000000, 0x10000)
        uc.mem_write(BASE, image)
        uc.mem_write(layout['base'], runtime)
        uc.mem_write(STOP, b'\x4e\x71')
        return uc

    for mode in (1, 2, 3):
        for track in range(7):
            for ping in (0, 1):
                uc = new_machine()
                visits = {'pre': 0, 'pf_frame': 0, 'builder': 0, 'noteoffs': []}

                def wr(at, value, size=4):
                    uc.mem_write(at, value.to_bytes(size, 'big'))

                def rd(at, size=4):
                    return int.from_bytes(uc.mem_read(at, size), 'big')

                def on_code(u, pc, size, _):
                    if pc in (STOP, PF_END):
                        u.emu_stop()
                    elif pc == symbols['pre']:
                        visits['pre'] += 1
                    elif pc == symbols['pf_frame']:
                        visits['pf_frame'] += 1
                    elif pc in (BUILDER, NOTEOFF):
                        sp = u.reg_read(R.UC_M68K_REG_A7)
                        if pc == BUILDER:
                            visits['builder'] += 1
                        else:
                            visits['noteoffs'].append(rd(sp + 4))
                        u.reg_write(R.UC_M68K_REG_A7, sp + 4)
                        u.reg_write(R.UC_M68K_REG_PC, rd(sp))

                uc.hook_add(UC_HOOK_CODE, on_code)

                def seed_inputs():
                    wr(0x80003c10, MIX)
                    wr(0x800000e0, ping)
                    # Stock publisher inputs: MAIN/CUE pair and XLV, per track.
                    for t in range(8):
                        wr(0x80000c60 + 4*t, (103 - 7*t) << 8, 2)
                        wr(0x80000c62 + 4*t, (31 + t) << 8, 2)
                        wr(0x80000c80 + 2*t, 0x7f00, 2)
                        wr(0x8000485a + 8*t, 0x1234 + t, 2)

                seed_inputs()

                def frame(gate, muted):
                    wr(0x800000dc, gate)
                    wr(0x80000008, (1 << (8 + track)) if muted else 0)
                    # Supply fresh pre-builder controls and pre-insert dry gains.
                    for bank in (0, 1):
                        for t in range(8):
                            rec = RECORDS + bank*512 + t*64
                            wr(rec + 6, 0x4000 + t, 2)
                            wr(rec + 10, 0x5000 + t, 2)
                            wr(rec + 24, ((90 - t) << 8) | (17 + t), 2)
                            wr(rec + 26, ((76 - t) << 8) | (60 if t == 0 else 33 + t), 2)
                            wr(rec + 56, effects[t], 2)
                    uc.reg_write(R.UC_M68K_REG_SR, 0x2000)
                    uc.reg_write(R.UC_M68K_REG_A7, STACK)
                    wr(STACK, STOP)
                    uc.emu_start(PUBLISH, STOP, count=10000)
                    check(uc.reg_read(R.UC_M68K_REG_PC) == STOP, 'mixer returned')
                    check(uc.reg_read(R.UC_M68K_REG_A7) == STACK + 4, 'mixer stack restored')
                    uc.reg_write(R.UC_M68K_REG_A7, STACK)
                    uc.emu_start(PF_HOOK, PF_END, count=10000)
                    check(uc.reg_read(R.UC_M68K_REG_PC) == PF_END, 'post-fader returned')
                    check(uc.reg_read(R.UC_M68K_REG_A7) == STACK, 'post-fader stack restored')
                    records = RECORDS + ping*512
                    return {
                        'main': [rd(MIX + t*8 + 2, 2) for t in range(8)],
                        'sends': [[rd(records + t*64 + n, 2) for n in (24, 26)] for t in range(8)],
                        'dry': [[rd(RECORDS + bank*512 + t*64 + n, 2) for n in (6, 10)]
                                for bank in (0, 1) for t in range(8)],
                        'unheld': rd(symbols['UNHELD'], 1),
                        'shadow': rd(symbols['SHADOW'], 1),
                    }

                states = [('ot_unmuted', frame(0, False)), ('ot_muted', frame(0, True)),
                          ('switched_muted', frame(mode, True)), ('held_next_frame', frame(mode, True)),
                          ('unmuted', frame(mode, False)), ('remuted', frame(mode, True))]
                baseline = states[0][1]
                check(baseline['main'] == [(103 - 7*t) << 8 for t in range(8)],
                      'baseline MAIN gains equal nonzero seeded stock inputs')
                check(baseline['sends'][track][0] & 0x7fff,
                      'baseline DEL has nonzero amplitude, excluding the tag')
                check(baseline['sends'][track][1] & (0x7f00 if track == 0 else 0x7fff),
                      'baseline REV has nonzero amplitude, excluding tag and held note')
                check(all(word & 0x8000 for word in baseline['sends'][track]),
                      'baseline DEL and REV retain their participation tags')
                check(baseline['sends'][7] == [(83 << 8) | 24, (69 << 8) | 40],
                      'baseline T8 RETURNS keeps both seeded controls unchanged')
                zero_words = [0x8000, 0x803c if track == 0 else 0x8000]
                for label, state in states[1:4]:
                    check(state['main'][track] == 0, label + ': MAIN remains zero')
                    check(state['sends'][track] == zero_words, label + ': no new send, tags/note retained')
                    check(state['unheld'] & (1 << track) == 0, label + ': muted track held')
                for label, state in states:
                    check(all(state['sends'][t] == baseline['sends'][t] for t in range(8) if t != track),
                          label + ': every other send and T8 return control unchanged')
                    check(all(state['main'][t] == baseline['main'][t] for t in range(8) if t != track),
                          label + ': every other MAIN gain unchanged')
                for label, state in states[4:]:
                    check(state['main'] == baseline['main'], label + ': no stale post-FX hold')
                    check(state['sends'] == baseline['sends'], label + ': normal coefficients restored')
                    check(state['unheld'] & (1 << track), label + ': UNHELD released')
                # OTFX supplies the mute through actual pre-insert gains. Other
                # modes use release/trig behavior, which this probe does not render.
                remuted = states[-1][1]
                for bank in (0, 1):
                    for t in range(8):
                        expected = [0, 0] if mode == 3 and t == track else [0x4000 + t, 0x5000 + t]
                        check(remuted['dry'][bank*8 + t] == expected, 'remute dry-word isolation')
                check(visits['pre'] == 6 and visits['pf_frame'] == 6 and visits['builder'] == 6,
                      'all installed paths entered each frame')
                check(visits['noteoffs'] == ([track, track] if mode == 1 else []),
                      'only target track receives transition/remute note-off')
                sequences.append({'mode': mode, 'source_track': track + 1, 'ping': ping,
                                  'states': dict(states), 'visits': dict(visits, noteoffs=list(visits['noteoffs']))})
                print(f'PASS mode={mode} T{track + 1} ping={ping}: OT mute hold, unmute, remute, companion isolation')

    positive_checks = checks
    # Fresh machine using the last fixture (mode 3, T7, ping 1): bypass only
    # the new hold before executing any code, so translated-code caching
    # cannot conceal the mutation. The positive cases used installed bytes.
    uc = new_machine()
    visits = {'pre': 0, 'pf_frame': 0, 'builder': 0, 'noteoffs': []}
    uc.hook_add(UC_HOOK_CODE, on_code)
    seed_inputs()
    hold = symbols['p1_hold']
    original = bytes(uc.mem_read(hold, 6))
    try:
        uc.mem_write(hold, b'\x4e\xf9' + symbols['p1_edge'].to_bytes(4, 'big'))
        control_baseline = frame(0, False)
        control_muted = frame(0, True)
        control_switched = frame(mode, True)
        check(control_muted['main'][track] == 0 and control_muted['sends'][track] == zero_words,
              'negative control starts correctly muted in OT')
        check(control_switched['main'][track] == control_baseline['main'][track] != 0,
              'negative control exposes the missing post-FX hold')
        check(control_switched['sends'][track] == control_baseline['sends'][track] != zero_words,
              'negative control catches the reopened send coefficients')
        negative = dict(caught=True, mode=mode, source_track=track + 1, ping=ping,
                        mutation='p1_hold replaced by jmp p1_edge only in emulator memory',
                        fresh_machine=True, patched_before_execution=True,
                        ot_muted=control_muted, switched=control_switched, executed_frames=3,
                        assertions=checks - positive_checks)
        print('PASS negative control: bypassed hold reopens the muted track send coefficients')
    finally:
        uc.mem_write(hold, original)

    receipt = {
        'passed': True, 'sequences': len(sequences), 'executed_frames': 6*len(sequences),
        'positive_assertions': positive_checks, 'assertions_including_negative_control': checks,
        'remix': args.remix,
        'image': str(args.image.resolve()), 'image_sha256': digest(image), 'runtime_sha256': digest(runtime),
        'runtime_base': layout['base'], 'runtime_bytes': len(runtime),
        'elf': str(args.elf.resolve()), 'elf_sha256': digest(args.elf.read_bytes()),
        'layout': str(args.layout.resolve()), 'layout_sha256': digest(args.layout.read_bytes()),
        'gate_sha256': digest(Path(__file__).read_bytes()),
        'executed': 'Installed stock mixer publisher, MUTE_MODES pre/p1_hold branches, installed POST FADER detour; both record banks and all seven source tracks',
        'stubbed': 'Stock DSP record builder preserves seeded records; note-off callback records target and returns. Mixer input gains, records, mute state, mode, and ping are seeded.',
        'not_claimed': 'DSP/audio rendering, tail decay, alternate-mode voice/retrigger behavior, live scheduler timing, hardware qualification; T8 controls unchanged does not prove rendered tails.',
        'symbols': {k: symbols[k] for k in ('pre', 'p1_hold', 'pf_frame', 'UNHELD', 'SHADOW')},
        'cases': sequences,
        'negative_control': negative,
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f'PASS {len(sequences)} sequences / {6*len(sequences)} installed frames + 3 negative-control frames / {checks} assertions')


if __name__ == '__main__':
    main()
