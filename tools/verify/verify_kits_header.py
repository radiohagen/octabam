#!/usr/bin/env python3
"""Execute linked KITS initialization against deliberately dirty record headers.

Build the selected KITS remix first. --build-root permits a plain-upstream
negative control without changing its firmware or this verifier's assertions.
"""
import argparse
import json
from pathlib import Path
import subprocess
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN
from unicorn.m68k_const import UC_CPU_M68K_CFV4E, UC_M68K_REG_A7, UC_M68K_REG_SR, UC_M68K_REG_PC


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build-root', type=Path, default=Path(__file__).resolve().parents[2])
    root = ap.parse_args().build_root
    rows = subprocess.check_output(['m68k-elf-nm', str(root / 'out/platform/runtime/runtime.elf')], text=True)
    symbols = {}
    for row in rows.splitlines():
        fields = row.split()
        if len(fields) == 3:
            symbols.setdefault(fields[2], set()).add(int(fields[0], 16))
    def one(name):
        values = symbols[name]
        assert len(values) == 1, (name, values)
        return next(iter(values))
    # The documented native/Scenes KITS record formats; other REC symbols
    # belong to unrelated linked modules and must not win by nm output order.
    record_sizes = symbols['REC'].intersection({6338, 10434})
    assert len(record_sizes) == 1, record_sizes
    rec = record_sizes.pop()
    count, start = one('NKITS'), one('KIMG') + one('O_LIB')
    assert count == 256
    u = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    u.ctl_set_cpu_model(UC_CPU_M68K_CFV4E)
    u.mem_map(0x40000000, 0x2000000)
    layout = json.loads((root / 'out/platform/layout.json').read_text())
    u.mem_write(layout['base'], (root / 'out/platform/runtime/runtime.bin').read_bytes())
    u.mem_write(start, b'\xa5' * (rec * count))
    stack, stop = 0x41ffe000, 0x41fff000
    u.mem_write(stack, stop.to_bytes(4, 'big'))
    u.reg_write(UC_M68K_REG_SR, 0x2000)
    u.reg_write(UC_M68K_REG_A7, stack)
    u.emu_start(one('lib_empty'), stop, count=4_000_000)
    assert u.reg_read(UC_M68K_REG_PC) == stop, 'initializer did not return'
    dirty = [n for n in range(count) if bytes(u.mem_read(start + n * rec, 16)) != bytes(16)]
    assert not dirty, f'{len(dirty)} Kit headers retained allocator bytes; first: {dirty[:8]}'
    assert all(bytes(u.mem_read(start + n * rec + 16, 16)) == b'\xa5' * 16 for n in range(count)), 'Part payload changed'
    print('[ok] all 256 dirty Kit headers cleared; adjacent Part payload bytes preserved')


if __name__ == '__main__':
    main()
