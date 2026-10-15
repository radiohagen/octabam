#!/usr/bin/env python3
"""Execute the installed first-sector fix; retain stock as a negative control."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import toolpath  # noqa: E402,F401
from remix import registry
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import (UC_CPU_M68K_CFV4E, UC_M68K_REG_A0,
    UC_M68K_REG_A1, UC_M68K_REG_A2, UC_M68K_REG_A3, UC_M68K_REG_A4,
    UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_D0,
    UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D3, UC_M68K_REG_D4,
    UC_M68K_REG_D5, UC_M68K_REG_D6, UC_M68K_REG_D7, UC_M68K_REG_PC,
    UC_M68K_REG_SR)

ROOT = Path(__file__).resolve().parents[2]
SITE, END = 0x40014cfe, 0x40014d58
PTR, LEFT, DATA = 0x46c8c594, 0x46c8c592, 0x900000a0
SRC, STACK = 0x46110000, 0x460ff000
STOCK = bytes.fromhex('207946c8c594')
AUTHOR_SHA = '14b22d23ccd0a4a209ff69f20d3ed5c5d25e889f1d7ffed65c8d23f9a3c5051b'


def main():
    remix = registry.remix(sys.argv[1] if len(sys.argv) > 1 else 'pio-write-fix')
    assert 'PIO WRITE FIX' in {m.key for m in registry.selected(remix)}
    image = (ROOT/'out/mainos_bus.bin').read_bytes()
    runtime = (ROOT/'out/platform/runtime/runtime.bin').read_bytes()
    base = json.loads((ROOT/'out/platform/layout.json').read_text())['base']
    raw = subprocess.check_output(['m68k-elf-nm', '--extern-only', '--defined-only',
        str(ROOT/'out/platform/runtime/runtime.elf')], text=True)
    sym = {f[2]: int(f[0], 16) for line in raw.splitlines() if len(f := line.split()) == 3}
    target = sym['pio_write_first']
    assert image[SITE-0x40000400:SITE-0x40000400+6] == b'\x4e\xf9'+target.to_bytes(4, 'big')
    assert hashlib.sha256(runtime[target-base:target-base+52]).hexdigest() == AUTHOR_SHA
    # Compare normalized instructions against the still-owned upstream body,
    # so the standalone source cannot silently become a different fix.
    stems = (ROOT/'modules/stems/stems.s').read_text()
    author = stems[stems.index('stems_ata_first:\n'):stems.index('| ---- creating the task')]
    standalone = (ROOT/'modules/pio-write-fix/first.s').read_text().split('pio_write_first:\n', 1)[1]
    def instructions(text):
        return [line.split('|')[0].strip() for line in text.splitlines()
                if line.split('|')[0].strip()]
    assert instructions(author.split('\n', 1)[1]) == instructions(standalone)
    u = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    u.ctl_set_cpu_model(UC_CPU_M68K_CFV4E)
    u.mem_map(0x40000000, 0x2000000)
    u.mem_map(0x46000000, 0x1000000)
    u.mem_map(0x90000000, 0x1000)
    u.mem_write(0x40000400, image)
    u.mem_write(base, runtime)
    u.hook_add(UC_HOOK_CODE, lambda cpu, pc, size, _: cpu.emu_stop() if pc == END else None)
    state = {}
    def write(cpu, access, addr, size, value, _):
        if addr != DATA:
            return
        assert size == 2
        state['words'].extend((value & 0xffff).to_bytes(2, 'big'))
        if len(state['words']) == 512:
            pointer = int.from_bytes(cpu.mem_read(PTR, 4), 'big')
            left = cpu.mem_read(LEFT, 1)[0]
            state['ready'] = (pointer, left)
            if state['interrupt']:
                assert (pointer, left) == (SRC+512, state['count']-1)
                if left:
                    assert bytes(cpu.mem_read(pointer, 512)) == state['payload'][512:1024]
                    cpu.mem_write(PTR, (pointer+512).to_bytes(4, 'big'))
                    cpu.mem_write(LEFT, bytes([left-1]))
    u.hook_add(UC_HOOK_MEM_WRITE, write, begin=DATA, end=DATA+1)
    kept = [UC_M68K_REG_D2, UC_M68K_REG_D3, UC_M68K_REG_D4, UC_M68K_REG_D5,
            UC_M68K_REG_D6, UC_M68K_REG_D7, UC_M68K_REG_A1, UC_M68K_REG_A2,
            UC_M68K_REG_A3, UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6]
    installed = bytes(u.mem_read(SITE, 6))
    cases = 0
    for stock in (True, False):
        for count in (1, 2, 4, 255):
            for interrupt in ((False,) if stock else (False, True)):
                payload = bytes((i*73+(i//512)*19) & 255 for i in range(1024))
                state.clear()
                state.update(words=bytearray(), count=count, payload=payload, interrupt=interrupt)
                u.mem_write(SRC, payload)
                u.mem_write(PTR, SRC.to_bytes(4, 'big'))
                u.mem_write(LEFT, bytes([count]))
                u.mem_write(SITE, STOCK if stock else installed)
                values = {reg: 0xabc00000+i for i, reg in enumerate(kept)}
                values[UC_M68K_REG_D2] = count
                u.reg_write(UC_M68K_REG_SR, 0x2000)
                u.reg_write(UC_M68K_REG_A7, STACK)
                u.reg_write(UC_M68K_REG_D0, 0xdeadbeef)
                u.reg_write(UC_M68K_REG_D1, 0x12345678)
                u.reg_write(UC_M68K_REG_A0, 0)
                for reg, value in values.items():
                    u.reg_write(reg, value)
                # Unicorn may cache translated code at the switched detour.
                u.ctl_remove_cache(SITE, SITE+6)
                u.emu_start(SITE, 0, count=4000)
                assert u.reg_read(UC_M68K_REG_PC) == END
                assert state['words'] == payload[:512]
                assert state['ready'] == ((SRC, count) if stock else (SRC+512, count-1))
                extra = int(interrupt and count > 1)
                assert int.from_bytes(u.mem_read(PTR, 4), 'big') == SRC+512*(1+extra)
                assert u.mem_read(LEFT, 1)[0] == count-1-extra
                assert u.reg_read(UC_M68K_REG_A7) == STACK
                assert all(u.reg_read(reg) == value for reg, value in values.items())
                assert u.reg_read(UC_M68K_REG_SR) & 0xff00 == 0x2000
                cases += 1
    print(f'[ok] PIO first sector: {cases} cases; original stock negative control, installed hook, exact author bytes, ordered data, immediate handler and preserved registers')


if __name__ == '__main__':
    main()
