#!/usr/bin/env python3
"""Execute POST FADER through the installed image detour on both record banks.

The stock builder is stubbed only in this micro gate so records can be varied
independently. verify_postfader.py covers the real builder and DSP audio.
"""
import json
import pathlib
import runpy
import tempfile
from types import SimpleNamespace
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import toolpath  # noqa: E402,F401
from remix import registry
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn import m68k_const as reg

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOK, END, BUILDER = 0x4000d0e4, 0x4000d0ea, 0x40004bd4
BASE, STACK, MIX = 0x40000400, 0x40fff000, 0x80006000


def main():
    remix = registry.remix(sys.argv[1])
    if 'POST FADER' not in remix.modules:
        print('[ -- ] no POST FADER'); return
    mods = registry.bound(remix)
    selected = {mods[k].menu.fx2_id for k in ('SEND', 'DELAY SERVER', 'REVERB SERVER') if k in remix.modules}
    send = mods['SEND'].menu.fx2_id
    delay = mods['DELAY SERVER'].menu.fx2_id if 'DELAY SERVER' in remix.modules else None
    verb = mods['REVERB SERVER'].menu.fx2_id if 'REVERB SERVER' in remix.modules else None
    if remix.fallback == 'SEND': selected.add(0)
    image = (ROOT / 'out/mainos_bus.bin').read_bytes()
    symbols = subprocess.check_output(['m68k-elf-nm', str(ROOT / 'out/platform/runtime/runtime.elf')], text=True)
    target = next(int(f[0], 16) for line in symbols.splitlines()
                  if len(f := line.split()) == 3 and f[2] == 'pf_frame')
    assert image[HOOK-BASE:END-BASE] == b'\x4e\xb9' + target.to_bytes(4, 'big')
    u = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    u.ctl_set_cpu_model(reg.UC_CPU_M68K_CFV4E)
    u.mem_map(0x40000000, 0x1000000); u.mem_map(0x80000000, 0x10000)
    u.mem_write(BASE, image)
    layout = json.loads((ROOT / 'out/platform/layout.json').read_text())
    u.mem_write(layout['base'], (ROOT / 'out/platform/runtime/runtime.bin').read_bytes())
    exercise(u, send, delay, verb, selected, 'installed hook')
    synthetic_ids()


def exercise(u, send, delay, verb, selected, label):
    untouched = next(i for i in range(64) if i not in selected)
    u.mem_write(BUILDER, bytes.fromhex('4e75'))
    u.hook_add(UC_HOOK_CODE, lambda cpu, pc, size, data: cpu.emu_stop() if pc == END else None)
    u.mem_write(0x80003c10, MIX.to_bytes(4, 'big'))
    registers = [getattr(reg, 'UC_M68K_REG_' + kind + str(n)) for kind in ('D', 'A') for n in range(8)]
    cases = 0
    for ping, variation, level in ((p, v, l) for p in (0, 1) for v in range(8) for l in range(128)):
        records = bytearray(b'\xa5' * 1024)
        expected = bytearray(records)
        gains = bytearray(b'\x3c' * 64)
        for t, effect in enumerate((0, send, delay if delay is not None else 6,
                                    verb if verb is not None else 7,
                                    untouched, 0x14, send, delay if delay is not None else 6)):
            off = ping * 512 + t * 64
            # Distinct knobs and dirty low bytes; low byte 60 is a held
            # TEMPO SYNC note for the delay, a fraction everywhere else.
            # Include no send, fraction-only, maximum, note-only and
            # a stale marker; original controls always mask to 15 bits.
            values = (0, 1, 0xff, 0x100, 0x7fff, 0x803c, 0xffff,
                      ((17*t + 63) % 128 << 8) | 0xfe)
            v0, v1 = values[(variation+t) % 8], values[(variation+t+3) % 8]
            for at, value in ((24, v0), (26, v1), (56, effect)):
                records[off+at:off+at+2] = value.to_bytes(2, 'big')
            l = (level + t * 17) % 128
            gains[t*8+2:t*8+4] = (l << 8).to_bytes(2, 'big')
        expected[:] = records
        for t in range(8):
            off = ping * 512 + t * 64
            effect = int.from_bytes(records[off+56:off+58], 'big')
            if effect not in selected: continue
            l = gains[t*8+2]
            for at in (24, 26):
                v = int.from_bytes(records[off+at:off+at+2], 'big') & 0x7fff
                out = v * l*l // 16384
                if effect == delay and at == 26:
                    out = (((v & 0x7f00) * l*l // 16384) & 0x7f00) | (v & 0xff)
                    participates = bool(v & 0x7f00)
                else:
                    participates = bool(v)
                out |= 0x8000 if participates else 0
                expected[off+at:off+at+2] = out.to_bytes(2, 'big')
        u.mem_write(0x80000110, bytes(records)); u.mem_write(MIX, bytes(gains))
        u.mem_write(0x800000e0, ping.to_bytes(4, 'big'))
        u.reg_write(reg.UC_M68K_REG_SR, 0x2000)
        before = {r: 0x12340000+i for i, r in enumerate(registers)}
        before[reg.UC_M68K_REG_A7] = STACK
        for r, v in before.items(): u.reg_write(r, v)
        u.emu_start(HOOK, 0, count=2000)
        assert u.reg_read(reg.UC_M68K_REG_PC) == END, (ping, level)
        got = bytes(u.mem_read(0x80000110, 1024))
        assert got == bytes(expected), (ping, level, variation, next((i, a, b) for i, (a, b) in enumerate(zip(got, expected)) if a != b))
        assert bytes(u.mem_read(MIX, 64)) == bytes(gains)
        assert all(u.reg_read(r) == v for r, v in before.items()), (ping, level, 'registers')
        cases += 1
    print(f'[ok] {label}: {cases} cases: both banks, every LEVEL, original participation, fractions, held notes, bound IDs, non-send records and registers')


def synthetic_ids():
    """Compile only the hook in private scratch: remapped IDs and absent engines.

    This proves the ColdFire selection contract, not a complete 64-ID firmware.
    It never overwrites shared out/ build products.
    """
    inc = runpy.run_path(str(ROOT / 'modules/post-fader/manifest.py'))['ids_inc']
    for ids, fallback in (({'SEND': 33, 'DELAY SERVER': 34, 'REVERB SERVER': 35}, 'SEND'),
                          ({'SEND': 39}, 'NONE')):
        modules = {key: SimpleNamespace(menu=SimpleNamespace(fx2_id=value)) for key, value in ids.items()}
        with tempfile.TemporaryDirectory(prefix='postfader-ids-') as tmp:
            d = pathlib.Path(tmp)
            (d / 'remix.inc').write_text(inc(modules, SimpleNamespace(fallback=fallback)))
            commands = (
                ['m68k-elf-as', '-mcpu=54455', '-I', str(d), '-o', str(d / 'hook.o'), str(ROOT / 'modules/post-fader/postfader.s')],
                ['m68k-elf-ld', '-Ttext=0x40200000', '-e', 'pf_frame', '-o', str(d / 'hook.elf'), str(d / 'hook.o')],
                ['m68k-elf-objcopy', '-O', 'binary', str(d / 'hook.elf'), str(d / 'hook.bin')],
            )
            for cmd in commands:
                subprocess.run(cmd, check=True, capture_output=True)
            u = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
            u.ctl_set_cpu_model(reg.UC_CPU_M68K_CFV4E)
            u.mem_map(0x40000000, 0x1000000); u.mem_map(0x80000000, 0x10000)
            u.mem_write(0x40200000, (d / 'hook.bin').read_bytes())
            u.mem_write(HOOK, bytes.fromhex('4eb940200000'))
            selected = set(ids.values()) | ({0} if fallback == 'SEND' else set())
            exercise(u, ids['SEND'], ids.get('DELAY SERVER'), ids.get('REVERB SERVER'), selected,
                     f'synthetic bound IDs {ids}, fallback {fallback}')


if __name__ == '__main__': main()
