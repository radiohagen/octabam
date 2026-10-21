"""Harmony fixture extending the shared native MIDI machine harness."""
import re
import subprocess
from midi_machine import ROOT, Machine as NativeMachine
from unicorn.m68k_const import *

def raw_scale(key,mode):
    return 1+key*2+(mode==5) if mode in (0,5) else 25+key*5+(1,2,3,4,6).index(mode)

MODES = [(0,2,4,5,7,9,11),(0,2,3,5,7,9,10),(0,1,3,5,7,8,10),
         (0,2,4,6,7,9,11),(0,2,4,5,7,9,10),(0,2,3,5,7,8,10),(0,1,3,5,6,8,10)]


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
    return {n:int(a,16) for a,n in re.findall(r'^([0-9a-f]+) [TtBbDdAa] ((?:seq|ed|hd|mh|bf|ms|ch|mp|ha)_\w+)$',raw,re.M)}


class Machine(NativeMachine):
    def instruction_limit(self, name):
        return 10000000

    def __init__(self, symbol_loader=symbols, artifact_root=None):
        super().__init__(symbol_loader, artifact_root)
        if 'bf_source_get' in self.sym:
            # Follow extends native NOTE SETUP defaults (biased SOURCE octave
            # and GRAV home). Read the selected image's descriptor, not a
            # pre-Follow constant copied from the stock-only fixture.
            for part in range(4):
                for track in range(8):
                    for field,descriptor in ((13,0x400d4035),(15,0x400d4037)):
                        address=0x400e21e0+0x8ed80+part*0x18b2+0x4e2+track*36+field
                        self.uc.mem_write(address,bytes(self.uc.mem_read(descriptor,1)))
        if 'mh_defaults' in self.sym:
            self.call('mh_defaults', stop=0x40025ace)

    def follow_write(self,field,data,track=0):
        """Seed the Follow fields in native Parts for module gates."""
        slots={'source':3,'mode':15,'response':12,'fixed':13,'offset':13,'home':15}
        for t,value in enumerate(data,track):
            address=self.part_address(t,slots[field])
            old=self.uc.mem_read(address,1)[0]
            if field=='mode':value=(old&0x0f)|((value&3)<<4)
            elif field=='response':value=(old&~2)|((value&1)<<1)
            elif field=='fixed':value=(old&0xf0)|(value&15)
            elif field=='offset':value=(old&0x0f)|(((value+2)&7)<<4)
            elif field=='home':value=(old&0xf0)|(value&15)
            self.uc.mem_write(address,bytes((value,)))
    def follow_read(self,field,count=8,track=0):
        slots={'source':3,'mode':15,'response':12,'fixed':13,'offset':13,'home':15}
        values=[]
        for t in range(track,track+count):
            value=self.uc.mem_read(self.part_address(t,slots[field]),1)[0]
            if field=='mode':value=(value>>4)&3
            elif field=='response':value=(value>>1)&1
            elif field in ('fixed','home'):value&=15
            elif field=='offset':value=(((value>>4)&7)-2)&255
            values.append(value)
        return bytes(values)
    def set_key(self,track,value):
        self.uc.mem_write(self.part_address(track,17),bytes((value,)))
        self.uc.mem_write(0x46c76df1+68*track,bytes((value,)))
    def harmony_state(self):
        return b''.join(bytes(self.uc.mem_read(self.part_address(t,f),1)) for t in range(8) for f in (5,16))
