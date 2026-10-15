#!/usr/bin/env python3
"""Check actual linked MIDI Scales code, native IDs, rounding and formatter bounds."""
import argparse
import midi_machine as h
from unicorn.m68k_const import *

def machine_gate():
    m=h.Machine();u=m.uc
    for key in range(12):
        for mode,degrees in enumerate(h.MODES):
            raw=h.raw_scale(key,mode)
            assert m.call('ms_decode',raw)==(key<<2)+(mode<<6)
            valid=[n for n in range(128) if (n-key)%12 in degrees]
            for n in range(128):
                want=min(valid,key=lambda v:(abs(v-n),v))
                assert m.call('ms_snap',n,raw)==want,(raw,n,want)
            m.set_key(0,raw)
            u.mem_write(0x100b14cc,b'\0')
            u.mem_write(m.scratch-1,b'\xa5'+b'?'*10+b'\xa5')
            # Formatter takes normal stack arguments.
            u.mem_write(m.stack+4,m.scratch.to_bytes(4,'big')+raw.to_bytes(4,'big'))
            m.call('ms_format')
            result=bytes(u.mem_read(m.scratch,10))
            assert result[:5].split(b'\0')[0].decode()==['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][key]
            assert result[5:].split(b'\0')[0].decode()==['MAJ','DOR','PHR','LYD','MIX','MIN','LOC'][mode]
            assert bytes(u.mem_read(m.scratch-1,1))==bytes(u.mem_read(m.scratch+10,1))==b'\xa5'
    for raw in [0,85,127,255]:
        assert m.call('ms_decode',raw)==0xffffffff
        assert m.call('ms_snap',61,raw)==61
    # Native setter receives the raw-ID delta for a musical-order movement.
    ordered=[0]+[h.raw_scale(key,mode) for key in range(12) for mode in range(7)]
    for ordinal,raw in enumerate(ordered):
        m.set_key(0,raw)
        for delta in (-100000,-4,-1,0,1,4,100000):
            u.mem_write(0x46c7d244+5*20,bytes(4))
            m.call('ms_encoder',5,stop=0x4007a3ea,regs={UC_M68K_REG_D5:delta & 0xffffffff})
            actual=u.reg_read(UC_M68K_REG_D5)
            target=ordered[max(0,min(84,ordinal+(1 if delta>=4 else -1 if delta<=-4 else 0)))]
            assert actual==(target-raw)&0xffffffff,(raw,delta,actual,target)
    for slot in range(5):m.call('ms_encoder',slot,stop=0x4007a4cc)
    if 'bf_source_get' in m.sym:
        m.follow_write('source',bytes((0,1,0,0,0,0,0,0)),0)
        u.mem_write(0x100b14cc,b'\x01')
        m.call('ms_encoder',5,stop=0x4007a6ba,regs={UC_M68K_REG_D5:1})
    if 'mh_get' in m.sym and 'bf_source_get' not in m.sym:
        # Harmony without Follow still separates the UI Part from playback.
        u.mem_write(0x100b14cf,b'\x01')
        u.mem_write(0x400e21e0+0x8ed80+0x18b2+0x4e2+17,b'\x06')
        u.mem_write(0x46c76df1,b'\x01')
        assert m.call('ms_raw_ui',0)==6
        assert m.call('ms_raw',0)==1
        print('  [ok] no-Follow Harmony KEY editor reads selected Part independently of playback')
    print('  [ok] scale encoder order, both end clamps, stock-control pass-through and inherited KEY guard')
    print('  [ok] linked MIDI Scales: 84 combinations x 128 pitches, native IDs preserved, OFF/invalid, formatter guards')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('remix',nargs='?');ap.parse_args();machine_gate()
