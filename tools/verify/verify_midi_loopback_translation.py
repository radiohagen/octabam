#!/usr/bin/env python3
"""Actual linked translation and native UART/queue bytes, not a Python mapper."""
import re
import subprocess
from verify_midi_loopback import Machine,ROOT,MSG,DONE,REGS,decode
from unicorn.m68k_const import *

def machine(route=2):
    raw=subprocess.check_output(['m68k-elf-nm',str(ROOT/'out/platform/runtime/runtime.elf')],text=True)
    sym={name:int(addr,16) for addr,name in re.findall(r'^([0-9a-f]+) [TtDdBb] (\w+)$',raw,re.M)}
    m=Machine(symbol_table=sym)
    m.put(0x46c82456,0x400e21e0)
    m.put(0x100b14cf,0,1)
    m.put('lb_routes',route,1)
    return m

def set_config(m,mode,source=60,target=84,radius=12,track=0,context=0):
    for field,value in enumerate((mode,source,target,radius)):
        assert m.call('lt_set',(context,track,field,value))==1

def send(m,msg,track=0,pc=0x4009fbb2):
    m.u.mem_write(MSG,bytes(msg))
    before=m.get(0x400b967c)
    m.call('lb_send',(3,MSG),regs={UC_M68K_REG_D7:track},return_pc=pc,stop=pc)
    assert bytes(m.u.mem_read(MSG,3))==bytes(msg),'producer packet mutated'
    n=m.get(0x400b967c)
    # Read the whole native output stream, since it may use running status.
    raw=bytes(m.u.mem_read(0x47004000+4096-n,n))[::-1]
    return decode(raw),n-before

def drain(m):
    out=[]
    while m.get('lb_head')!=m.get('lb_tail'): out.append(list(m.next()))
    return out

def main():
    subprocess.run(['python3',str(ROOT/'modules/midi-loopback/upstream/modules/midi-loopback/generate_translation.py'),'--check'],check=True)
    m=machine()
    # Independent oracle: exhaustive input pitches at both MIDI edges, radius
    # zero, the OT window and maximum radius. Never wrap/clamp an overflow.
    for source in (0,60,127):
        for target in (0,84,127):
            for radius in (0,12,63):
                for note in range(128):
                    mapped=note+target-source
                    expected=mapped if abs(note-source)<=radius and 0<=mapped<=127 else 0xffffffff
                    assert m.call('lt_map',(note,source,target,radius))==expected
    print('[ok] 3456 symmetric range cases: radius zero, inclusive bounds and MIDI-edge DROP',flush=True)
    for invalid in (64,127,128):
        assert m.call('lt_map',(60,60,84,invalid))==0xffffffff
        assert m.call('lt_set',(0,0,3,invalid))==0
        assert m.call('lt_get',(0,0,3))==12
    for radius in (0,12,63):
        m.call('lt_range_format',(MSG,2*radius))
        assert bytes(m.u.mem_read(MSG,len(str(radius))+2))==b'\xb1'+str(radius).encode()+b'\0'
    for route in range(3):
        for mode in range(4):
            m=machine(route);set_config(m,mode)
            cumulative_ext=[]
            for source in (48,60,62,72,47,73,0,127):
                expected_int=[];expected_ext=[]
                for on in (True,False):
                    msg=[0x90 if on else 0x80,source,101 if on else 17]
                    ext,_=send(m,msg,pc=0x4009fbb2 if on else 0x4009f8c2)
                    for enabled,bit,expected in ((route!=0,1,expected_int),(route!=1,2,expected_ext)):
                        pitch=source+24 if mode&bit else source
                        if enabled and (not mode&bit or 72<=pitch<=96):
                            expected.append([msg[0],pitch,msg[2]])
                    # EXT is cumulative over this fresh machine.
                    if on: internal=drain(m)
                    else: internal+=drain(m)
                assert internal==expected_int,(route,mode,source,internal,expected_int)
                cumulative_ext+=expected_ext
                assert ext==cumulative_ext,(route,mode,source,ext,cumulative_ext)
                assert m.get('lb_internal_held')==0
                assert bytes(m.u.mem_read(m.sym['lb_owned'],2048))==bytes(2048)
            # Notes only: velocity and every control byte must be unchanged.
            m.u.mem_write(MSG,bytes((0xb0,34,117)))
            before=m.get(0x400b967c)
            m.call('lb_track_send',(3,MSG),regs={UC_M68K_REG_D7:0})
            assert drain(m)==([[0xb0,34,117]] if route else [])
            assert (m.get(0x400b967c)>before)==(route!=1)
    print('[ok] all route/apply pairs, raw OFF, OT preset, inclusive bounds/DROP, note-off velocity and immutable packets',flush=True)

    # Mapping edits flush the old translated pitch, then absorb late releases.
    for field,value in ((0,0),(1,59),(2,85),(3,11)):
        m=machine();set_config(m,3)
        send(m,(0x90,60,100));assert drain(m)==[[0x90,84,100]]
        assert m.call('lt_set',(0,0,field,value))==1
        assert drain(m)==[[0x80,84,0]]
        n=m.get(0x400b967c)
        send(m,(0x80,60,0),pc=0x4009f8c2)
        assert not drain(m) and m.get(0x400b967c)==n
    print('[ok] every mapping edit releases admitted pitch and tombstones late stock releases',flush=True)

    for old,new in ((0,3),(1,2),(2,1),(3,0)):
        m=machine();set_config(m,old)
        internal=84 if old&1 else 60;external=84 if old&2 else 60
        send(m,(0x90,60,100));assert drain(m)==[[0x90,internal,100]]
        assert m.call('lt_set',(0,0,0,new))==1
        assert drain(m)==[[0x80,internal,0]]
        ext,_=send(m,(0x80,60,17),pc=0x4009f8c2)
        assert ext==[[0x90,external,100],[0x80,external,0]] and not drain(m)
    print('[ok] enable/disable and INT↔EXT changes release each copy at its own cached pitch',flush=True)

    # Two raw pitches from two tracks can map to the same destination pitch.
    m=machine();m.put(m.sym['lb_routes']+1,2,1)
    set_config(m,3);set_config(m,3,source=62,track=1)
    send(m,(0x90,60,100));send(m,(0x90,62,100),track=1)
    assert drain(m)==[[0x90,84,100]]
    send(m,(0x80,60,0),pc=0x4009f8c2);assert not drain(m)
    send(m,(0x80,62,0),track=1,pc=0x4009f8c2)
    assert drain(m)==[[0x80,84,0]]
    assert m.get('lb_internal_held')==0
    print('[ok] translated-pitch collisions share destination ownership until the final release',flush=True)

    # Route/channel/playing-Part changes release the cached original output.
    for change in ('route','channel','part'):
        m=machine();set_config(m,3)
        m.put(0x40171442+12,8,1)
        m.call('lb_part_sync');m.call('lb_sync')
        send(m,(0x90,60,100));assert drain(m)==[[0x90,84,100]]
        if change=='route': m.call('lb_set_route',(0,0))
        elif change=='channel':
            m.put(0x46c76de0,2,1);m.call('lb_sync')
        else:
            m.put(0x80006676,1,1);m.call('lb_part_sync')
        assert drain(m)==[[0x80,84,0]],change
        n=m.get(0x400b967c)
        send(m,(0x80,60,0),pc=0x4009f8c2)
        assert not drain(m) and m.get(0x400b967c)==n,change
    print('[ok] route/channel/Part changes release original translated identities without late duplicate releases',flush=True)

    # Real live-key producer: UI Part differs from sequencer Part.
    import verify_midi_loopback_producers as producers
    sym=machine().sym
    m=producers.prepare(0,2,symbol_table=sym)
    set_config(m,3,context=1);m.put(0x100b14cf,1,1)
    m.put(0x40171442+0x18b2,1,1);m.put(0x40171442+0x18b2+12,8,1)
    m.call(0x4009e9a8,(0,60,100,0));m.call(0x4009e9a8,(0,60,0,0))
    assert drain(m)==[[0x90,84,100],[0x90,84,0]]
    print('[ok] native live keys use the selected Part mapping and velocity-zero releases',flush=True)

    # Existing source/receiver/control regressions also run with mapping ON.
    # Identity references keep their independent byte-level expectations valid.
    original=producers.prepare
    def enabled(track,route,channel=1,**kwargs):
        m=original(track,route,channel,symbol_table=sym)
        for part in (0,1):
            for t in range(8):set_config(m,3,target=60,radius=63,track=t,context=part)
        return m
    producers.prepare=enabled
    try:
        producers.feedback()
        producers.overlapping_sources()
        producers.feedback_guard_controls()
    finally: producers.prepare=original
    print('[ok] enabled mapping preserves receiver feedback barriers and control-message delivery rules',flush=True)

if __name__=='__main__': main()
