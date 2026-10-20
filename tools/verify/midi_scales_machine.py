#!/usr/bin/env python3
"""Machine-code harness for MIDI Scales verification. No firmware is bundled."""
import re
import subprocess
from midi_machine import ROOT, Machine as NativeMachine, dram_map_size

def raw_scale(key,mode):
    return 1+key*2+(mode==5) if mode in (0,5) else 25+key*5+(1,2,3,4,6).index(mode)

MODES = [(0,2,4,5,7,9,11),(0,2,3,5,7,9,10),(0,1,3,5,7,8,10),
         (0,2,4,6,7,9,11),(0,2,4,5,7,9,10),(0,2,3,5,7,8,10),(0,1,3,5,6,8,10)]


def symbols():
    raw = subprocess.check_output(['m68k-elf-nm', str(ROOT/'out/platform/runtime/runtime.elf')], text=True)
    return {n:int(a,16) for a,n in re.findall(r'^([0-9a-f]+) [Tt] (ms_\w+)$',raw,re.M)}

class Machine(NativeMachine):
    def __init__(self, symbol_loader=symbols, artifact_root=None):
        super().__init__(symbol_loader, artifact_root)

    def set_key(self, track, value):
        # Standalone Scales reads the native shadow; HARM reads the Part's
        # authoritative KEY. Seed both as a real native KEY edit does.
        self.uc.mem_write(self.part_address(track, 17), bytes((value,)))
        self.uc.mem_write(0x46c76df1 + 68 * track, bytes((value,)))
