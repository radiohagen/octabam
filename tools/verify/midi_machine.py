#!/usr/bin/env python3
"""Shared machine-code harness for MIDI module verification. No firmware is bundled."""
import json
import pathlib
import re
import subprocess
import sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import toolpath
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import *

def raw_scale(key,mode):
    return 1+key*2+(mode==5) if mode in (0,5) else 25+key*5+(1,2,3,4,6).index(mode)

MODES = [(0,2,4,5,7,9,11),(0,2,3,5,7,9,10),(0,1,3,5,7,8,10),
         (0,2,4,6,7,9,11),(0,2,4,5,7,9,10),(0,2,3,5,7,8,10),(0,1,3,5,6,8,10)]


def dram_map_size(layout):
    """Cover stock RAM and the selected runtime, staging and retained state."""
    end = max(0x41000000, layout['top'], layout['stage_end'], layout['ceiling'])
    return (end - 0x40000000 + 4095) & ~4095


class InterruptMaskTrace:
    """Observe IPL without materializing Unicorn's lazy comparison flags.

    Reading SR on every instruction can change a ColdFire CMP/BNE result in
    Unicorn. Decode the actual SR writers instead; refuse an unknown writer
    so a new instruction cannot silently invalidate the measurement.
    """
    def __init__(self, uc, ipl=0):
        self.uc=uc;self.ipl=ipl
    def before(self, pc):
        u=self.uc;old=self.ipl
        op=int.from_bytes(u.mem_read(pc,2),'big')
        if op==0x46fc:
            self.ipl=(int.from_bytes(u.mem_read(pc+2,2),'big')>>8)&7
        elif op&0xfff8==0x46c0:
            self.ipl=(u.reg_read(UC_M68K_REG_D0+(op&7))>>8)&7
        elif op&0xffc0==0x46c0 or op in (0x007c,0x027c,0x0a7c,0x4e73):
            raise AssertionError(('unhandled SR writer',hex(pc),hex(op)))
        return old

def symbols():
    raw = subprocess.check_output(['m68k-elf-nm', str(ROOT/'out/platform/runtime/runtime.elf')], text=True)
    return {n:int(a,16) for a,n in re.findall(r'^([0-9a-f]+) [Tt] ((?:hd|mh|bf|ms)_\w+)$',raw,re.M)}

class Machine:
    def __init__(self, symbol_loader=symbols, artifact_root=None):
        self.sym=symbol_loader(); self.uc=Uc(UC_ARCH_M68K,UC_MODE_BIG_ENDIAN)
        out = artifact_root or ROOT/'out'
        layout = json.loads((out/'platform/layout.json').read_text())
        self.initial_sr = 0x2700
        u=self.uc; u.ctl_set_cpu_model(UC_CPU_M68K_CFV4E)
        # The combined image's linked BSS can extend beyond the former 16 MiB
        # test map. Cover the declared runtime/retained reservation, as the
        # full firmware port does, instead of faulting on valid state writes.
        dram_size = dram_map_size(layout)
        for a,n in [(0x40000000,dram_size),(0x46000000,0x200000),(0x47000000,0x10000),(0x46c70000,0x20000),(0x10000000,0x200000),(0x80000000,0x10000)]:u.mem_map(a,n)
        u.mem_write(0x40000400,(out/'mainos_bus.bin').read_bytes())
        self.base=layout['base']
        u.mem_write(self.base,(out/'platform/runtime/runtime.bin').read_bytes())
        self.stack=0x47008000;self.done=0x4700fff0;self.scratch=0x47001000
        self.stops={self.done}; self.arrival=None;self.writes=[]
        u.hook_add(UC_HOOK_CODE,self.stop)
        u.hook_add(UC_HOOK_MEM_WRITE,lambda u,a,p,n,v,x:self.writes.append((p,n)))
        # A native fresh Part fixture, with UI and all engine tracks on bank 0
        # Part 0. Tests may move either context independently.
        u.mem_write(0x46c82456,(0x400e21e0).to_bytes(4,'big'))
        for p in range(4):
            for t in range(8):
                u.mem_write(0x400e21e0+0x8ed80+p*0x18b2+0x4e2+t*36+13,b'\x03')
                u.mem_write(0x400e21e0+0x8ed80+p*0x18b2+0x4e2+t*36+15,b'\x02')
        if 'mh_defaults' in self.sym:self.call('mh_defaults',stop=0x40025ace)
    def part_address(self,track,field):
        bank=int.from_bytes(self.uc.mem_read(0x46c82456,4),'big')
        part=self.uc.mem_read(0x100b14cf,1)[0]
        return bank+0x8ed80+part*0x18b2+0x4e2+track*36+field
    def follow_write(self,field,data,track=0):
        """Seed native Part bytes, including deliberately corrupt routing data."""
        slots={'source':3,'mode':12,'fixed':13,'offset':15,'response':12}
        for t,v in enumerate(data,track):
            a=self.part_address(t,slots[field])
            if field=='mode':v=(self.uc.mem_read(a,1)[0]&2)|(v&1)
            if field=='response':v=(self.uc.mem_read(a,1)[0]&1)|((v&1)<<1)
            if field=='offset':v=(v+2)&255
            self.uc.mem_write(a,bytes((v,)))
    def follow_read(self,field,count=8,track=0):
        slots={'source':3,'mode':12,'fixed':13,'offset':15,'response':12}
        values=[]
        for t in range(track,track+count):
            v=self.uc.mem_read(self.part_address(t,slots[field]),1)[0]
            if field=='mode':v&=1
            if field=='response':v=(v>>1)&1
            if field=='offset':v=(v-2)&255
            values.append(v)
        return bytes(values)
    def harmony_state(self):
        return b''.join(bytes(self.uc.mem_read(self.part_address(t,f),1))
                        for t in range(8) for f in (5,16))
    def set_key(self,track,value):
        self.uc.mem_write(self.part_address(track,17),bytes((value,)))
        self.uc.mem_write(0x46c76df1+68*track,bytes((value,)))
    def stop(self,u,p,n,x):
        if p in self.stops:self.arrival=p;u.emu_stop()
    def call(self,name,d0=0,d1=0,a0=None,stop=None,regs=None):
        u=self.uc;self.stops={stop or self.done};self.arrival=None;self.writes=[]
        u.reg_write(UC_M68K_REG_SR,self.initial_sr);u.reg_write(UC_M68K_REG_A7,self.stack)
        u.mem_write(self.stack,self.done.to_bytes(4,'big'))
        u.reg_write(UC_M68K_REG_D0,d0);u.reg_write(UC_M68K_REG_D1,d1)
        if a0 is not None:u.reg_write(UC_M68K_REG_A0,a0)
        for r,v in (regs or {}).items():u.reg_write(r,v)
        u.emu_start(self.sym[name],0,count=self.instruction_limit(name))
        assert self.arrival in self.stops,(name,hex(u.reg_read(UC_M68K_REG_PC)))
        return u.reg_read(UC_M68K_REG_D0)
    def instruction_limit(self, name):
        # Degree mode boundaries include bank conversion and a retained
        # snapshot; their correctness gate exercises those complete paths.
        return 10000000 if "hd_set" in self.sym else 20000
