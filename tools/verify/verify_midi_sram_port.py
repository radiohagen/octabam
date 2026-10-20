#!/usr/bin/env python3
"""Stock/candidate native SRAM lifecycle comparison under the full port.

Run after building REMIX=midi-sram. Uses a scratch virtual card only.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path
import verify_midi_harmony_port as port
from harmony_machine import ROOT
from verify_midi_sram import BASE, B, SIZE, OFFSETS


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',required=True,type=Path)
    args=ap.parse_args()
    port.OUT=ROOT/'out/midi-sram/port';port.OUT.mkdir(parents=True,exist_ok=True)
    w=port.fixture(args.project,'lifecycle',{},first_note=48)
    stock=ROOT/'out/raw/section_3_MAIN_OS.bin'
    candidate=ROOT/'out/mainos_bus.bin'
    port.run(w,'base',['--sequencer','--internal-clock','--frames','1','--mem-dump',f'0x10000000,0x100000={w}/seed.bin'],image=stock)
    seed=bytearray((w/'seed.bin').read_bytes());rng=random.Random(667)
    pool=rng.randbytes(len(OFFSETS))
    for off,value in zip(OFFSETS,pool):seed[BASE-0x10000000+off]=value
    (w/'seed.bin').write_bytes(seed)
    # These are complete native operations, running on the real RTOS.
    # Explicit calls make pattern/track/page boundaries deterministic.
    calls=[('clear-first-track','0x40039b00,0,0,1'),
           ('clear-last-track','0x40039b00,15,7,1'),
           ('clear-page','0x4003967c,7,3,2'),
           ('clear-held-locks','0x40040d44,6,4,3,65535'),
           ('copy-trig','0x4002bd2c,0x460c8122,0,0,0,1'),
           ('paste-trig','0x4002c4d4,0x460c8122,7,3,3,32768'),
           ('paste-page','0x4002ab50,0x460c8122,12,6,2'),
           ('clear-masked','0x40038668,255,0,4294967295'),
           ('duplicate-midi-page','0x4009c8bc,0,1,4294967295,1'),
           ('toggle-midi-trig','0x4005fb44,0,0'),
           ('copy-pattern',f'0x40020898,{BASE+0x8ed8:#x},{B:#x},0x8ed8'),
           ('copy-track',f'0x40020898,{BASE+0x48d0:#x},{B+0x48d0+7*0x8b0:#x},0x8b0'),
           ('copy-bank-to-cs1','0x4000faf0,0')]
    images=(('stock',stock),('protected',candidate))
    results={}
    for name,image in images:
        extra=['--cs1-in',w/'seed.bin','--no-post','--sequencer','--internal-clock','--frames','1']
        for tag,call in calls:
            if tag=='toggle-midi-trig':
                extra+=['--step','-:poke:0x80000012=0;0x80000013=0;0x80000014=0;0x80000015=1;0x100b14cc=0;0x100b14d0=0;0x460d1a9e=0;0x460d1a9f=1']
            extra += ['--step','-:call:'+call,'--step',f'-:dump:{BASE:#x},{SIZE}={w}/{name}-{tag}.bin']
        extra+=['--mem-dump',f'0x10000000,0x100000={w}/{name}-cs1.bin;{B:#x},{SIZE}={w}/{name}-bank.bin']
        port.run(w,name,extra,image=image)
    pool_set=set(OFFSETS)
    checked=[]
    for tag,_ in calls:
        raw=(w/f'stock-{tag}.bin').read_bytes();actual=(w/f'protected-{tag}.bin').read_bytes()
        assert bytes(actual[o] for o in OFFSETS)==pool,(tag,'pool overwritten')
        differences=[i for i,(a,b) in enumerate(zip(raw,actual)) if a!=b and i not in pool_set]
        assert not differences,(tag,differences[:10])
        checked.append(tag)
    native=(w/'protected-bank.bin').read_bytes()
    assert all(native[o]==255 for o in OFFSETS),'pool leaked into native DRAM'
    # Restart the result again, without LOAD PROJECT, then play both images.
    for name,image in images:
        events=port.run(w,name+'-resume',['--cs1-in',w/f'{name}-cs1.bin','--no-post',
            '--sequencer','--internal-clock','--frames','7000','--mem-dump',
            f'{BASE:#x},{SIZE}={w}/{name}-resumed.bin'],image=image,card=w/f'{name}-card.img')
        results[name]=events
    assert results['stock']==results['protected'],'MIDI differs after native operations and restart'
    resumed=(w/'protected-resumed.bin').read_bytes()
    assert bytes(resumed[o] for o in OFFSETS)==pool,'second restart lost pool'
    result={'pool_bytes':len(pool),'full_port_operations':checked,
            'native_pattern_bytes_match_stock':True,'retained_restarts':2,
            'midi_exact_after_restart':True,'midi_events':len(results['stock']),
            'image_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
            'hardware_tested':False}
    (port.OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
