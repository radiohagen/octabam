#!/usr/bin/env python3
"""Installed MIDI drawer bridge, stock oracle and unbridged negative control."""
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import toolpath  # noqa: F401,E402
from remix import registry
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn.m68k_const import (UC_CPU_M68K_CFV4E, UC_M68K_REG_A0,
    UC_M68K_REG_A1, UC_M68K_REG_A2, UC_M68K_REG_A3, UC_M68K_REG_A4,
    UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_D0,
    UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D3, UC_M68K_REG_D4,
    UC_M68K_REG_D5, UC_M68K_REG_D6, UC_M68K_REG_D7, UC_M68K_REG_PC)
ROOT = Path(__file__).resolve().parents[2]
BASE, SITE, END, STACK = 0x40000400, 0x400449ae, 0x400449c0, 0x460ff000

def main():
    remix = registry.remix(sys.argv[1])
    assert {'SCALE QUANTIZER', 'QUANTIZER MIDI DRAWER'} <= set(remix.modules)
    image = (ROOT/'out/mainos_bus.bin').read_bytes()
    stock = (ROOT/'out/raw/section_3_MAIN_OS.bin').read_bytes()
    runtime = (ROOT/'out/platform/runtime/runtime.bin').read_bytes()
    base = json.loads((ROOT/'out/platform/layout.json').read_text())['base']
    nm = subprocess.check_output(['m68k-elf-nm', '--extern-only', '--defined-only',
        str(ROOT/'out/platform/runtime/runtime.elf')], text=True)
    sym = {f[2]: int(f[0],16) for line in nm.splitlines() if len(f:=line.split()) == 3}
    assert image[SITE-BASE:SITE-BASE+6] == b'\x4e\xf9'+sym['qz_midi_octave'].to_bytes(4,'big')
    assert image[0x400449b8-BASE:0x400449c0-BASE] == b'\x4e\xf9'+sym['qz_octnum'].to_bytes(4,'big')+b'\x4e\x71'
    kept = (UC_M68K_REG_D1,UC_M68K_REG_D2,UC_M68K_REG_D3,UC_M68K_REG_D4,
            UC_M68K_REG_D5,UC_M68K_REG_D6,UC_M68K_REG_D7,UC_M68K_REG_A0,
            UC_M68K_REG_A1,UC_M68K_REG_A2,UC_M68K_REG_A3,UC_M68K_REG_A4,
            UC_M68K_REG_A5,UC_M68K_REG_A6)
    cases=0
    for mode in ('stock','unbridged','installed'):
        u=Uc(UC_ARCH_M68K,UC_MODE_BIG_ENDIAN);u.ctl_set_cpu_model(UC_CPU_M68K_CFV4E)
        u.mem_map(0x40000000,0x2000000);u.mem_map(0x46000000,0x1000000)
        u.mem_write(BASE,image);u.mem_write(base,runtime)
        if mode != 'installed':u.mem_write(SITE,stock[SITE-BASE:SITE-BASE+6])
        if mode == 'stock':u.mem_write(0x400449b8,stock[0x400449b8-BASE:END-BASE])
        u.hook_add(UC_HOOK_CODE,lambda cpu,pc,size,_:cpu.emu_stop() if pc==END else None)
        for octave in range(11):
            sentinels={reg:0x12340000+i for i,reg in enumerate(kept)}
            for reg,value in sentinels.items():u.reg_write(reg,value)
            u.reg_write(UC_M68K_REG_A7,STACK);u.mem_write(STACK-4,b'\xa5'*8)
            u.mem_write(0x400beba2,octave.to_bytes(4,'big'))
            u.emu_start(SITE,0,count=30)
            assert u.reg_read(UC_M68K_REG_PC)==END,(mode,octave)
            expected=(octave-1)&0xffffffff
            assert u.reg_read(UC_M68K_REG_D0)==expected
            assert all(u.reg_read(reg)==v for reg,v in sentinels.items())
            if mode=='unbridged':
                assert u.reg_read(UC_M68K_REG_A7)==STACK
                assert bytes(u.mem_read(STACK-4,4))==b'\xa5'*4
            else:
                assert u.reg_read(UC_M68K_REG_A7)==STACK-4
                assert int.from_bytes(u.mem_read(STACK-4,4),'big')==expected
            assert bytes(u.mem_read(STACK,4))==b'\xa5'*4
            cases+=1
    print(f'[ok] MIDI chromatic drawer: {cases} cases; stock oracle, unbridged missing-argument control, installed hook, native octave, stack and registers')
if __name__=='__main__':main()
