#!/usr/bin/env python3
"""Part-scoped UI/playback settings and real linked MIDI consumers."""
import re
import subprocess
from midi_machine import Machine, ROOT
from unicorn.m68k_const import *

B = 0x400e21e0
BS = 0x9b340
PS = 0x18b2


def symbols():
    raw = subprocess.check_output(['m68k-elf-nm', str(ROOT/'out/platform/runtime/runtime.elf')], text=True)
    return {n:int(a,16) for a,n in re.findall(r'^([0-9a-f]+) [TtBb] ((?:bf|mp)_\w+)$',raw,re.M)}


def main():
    m=Machine(symbols); u=m.uc
    def byte(a,v):u.mem_write(a,bytes((v,)))
    def ui(bank,part):
        u.mem_write(0x46c82456,(B+bank*BS).to_bytes(4,'big'));byte(0x100b14cf,part)
    def at(bank,part,track,field):return B+bank*BS+0x8ed80+part*PS+0x4e2+track*36+field
    def play(track,bank,part):byte(0x8000182a+track,bank);byte(0x80001832+track,part)
    for bank in range(2):
        for part in range(4):
            for track in range(8):
                byte(at(bank,part,track,13),3);byte(at(bank,part,track,15),2)
                byte(at(bank,part,track,17),1)
    ui(0,0)
    for t in range(8):play(t,1,2)
    # YES refreshes only module-owned staged values in the selected Part.
    # Execute the real detour and stop after the displaced native prologue.
    for part in range(4):
        ui(0,part)
        for track in range(8):
            byte(0x100b14cc,track)
            staged=[4,17,29,7,31,0]
            u.mem_write(0x460d5cb4,b''.join(v.to_bytes(4,'big') for v in staged))
            byte(at(0,part,track,3),2);byte(at(0,part,track,5),1)
            expected=staged[:]
            if 'bf_source_get' in m.sym:expected[3]=2
            m.sym['native_note_confirm']=0x4004af20
            m.call('native_note_confirm',stop=0x4004af28)
            actual=[int.from_bytes(u.mem_read(0x460d5cb4+4*i,4),'big') for i in range(6)]
            assert actual==expected,(part,track,actual,expected)
            byte(at(0,part,track,3),0);byte(at(0,part,track,5),0)
    ui(0,0);byte(0x100b14cc,0)
    print('  [ok] NOTE SETUP YES keeps live RFOL across all tracks/Parts and preserves stock staged fields')
    if 'bf_select' in m.sym:
        ui(0,0)
        m.call('bf_select',1,1)
        assert m.call('bf_source_get',1)==1
        assert m.call('bf_source_play',1)==0
        m.call('bf_reg_change',1,1,regs={UC_M68K_REG_D2:2})
        assert m.call('bf_oct_get',1)==5
        m.call('bf_reg_change',1,0,regs={UC_M68K_REG_D2:1})
        m.call('bf_reg_change',1,1,regs={UC_M68K_REG_D2:-1 & 0xffffffff})
        assert m.call('bf_oct_get',1)==0xffffffff
        m.call('bf_response_set',1,1)
        assert m.call('bf_mode_get',1)==1 and m.call('bf_response_get',1)==1
        m.call('bf_reg_change',1,0,regs={UC_M68K_REG_D2:-1 & 0xffffffff})
        assert m.call('bf_oct_get',1)==5 and m.call('bf_response_get',1)==1
        assert m.call('bf_response_play',1)==0
        # Receiver T2 reads its playing Part; T1 supplies its own context.
        byte(at(1,2,1,3),1);byte(at(1,2,1,13),4)
        u.mem_write(m.sym['bf_roots'],bytes((38,255,255,255,255,255,255,255)))
        assert m.call('bf_source_resolve',1)==0
        assert m.call('bf_register',0,1)==50
        # Chain crosses a different Part on T1; cycle fallback is bounded.
        play(0,0,1);byte(at(0,1,0,3),3)
        assert m.call('bf_source_resolve',1)==2
        byte(at(1,2,2,3),2)
        assert m.call('bf_source_resolve',1)==1
        print('  [ok] Follow independent octaves, packed response, per-track playback chains and cycle fallback')


if __name__=='__main__':main()
