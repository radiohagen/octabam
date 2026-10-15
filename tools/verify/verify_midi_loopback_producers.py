#!/usr/bin/env python3
"""Execute stock track producers through the installed routing adapters."""
from verify_midi_loopback import Machine, MSG, REGS, STACK, DONE, decode, symbols, Q
import re
import subprocess
from verify_midi_loopback import ROOT
from unicorn.m68k_const import *


def prepare(track, route, channel=1):
    m = Machine()
    m.put(0x46c82456, 0x400e21e0)
    for t in range(8):
        m.put(0x40171442 + 36*t, channel, 1)
        m.put(0x40171442 + 36*t + 12, route*4 if t == track else 0, 1)
        m.put(0x46c76de0 + 68*t, channel, 1)
    m.put('lb_routes', 0, 1)
    m.put(m.sym['lb_routes'] + track, route, 1)
    m.u.mem_write(0x46c78152, b'\xff'*2048)
    m.u.mem_write(0x46c79d70, b'\xff'*256)
    m.u.mem_write(0x46c76100, b'\xff'*2048)
    m.u.mem_write(0x46c76990, b'\xff'*32)
    m.u.mem_write(0x46c7a16c, b'\xff'*16)
    m.u.mem_write(0x46c7a9b6, b'\xff'*16)
    if 'usbmidi_up' in m.sym:
        m.put('usbmidi_up', 1, 1)
        m.put('usbmidi_tx_busy', 1, 1)
    return m


def outputs(m, expected, route):
    raw = b''.join(bytes(msg) for msg in expected) if route != 1 else b''
    n = m.get(0x400b967c)
    assert decode(bytes(m.u.mem_read(0x47004000+4096-n, n))[::-1]) == ([list(x) for x in expected] if route != 1 else []), (route, expected, n)
    if 'usbmidi_up' in m.sym:
        assert m.get('usbmidi_tx_acc_len', 2) == len(raw)
    internal = expected if route else []
    assert m.get('lb_accepted') == len(internal), (route, expected, m.get('lb_accepted'))
    for msg in internal:
        assert m.next() == bytes(msg).ljust(3, b'\0'), msg
    assert m.get('lb_head') == m.get('lb_tail')


def main():
    for track in range(8):
        for route in range(3):
            m = prepare(track, route)
            m.call(0x4009e9a8, (track, 84, 100, 0))
            m.call(0x4009e9a8, (track, 84, 0, 0))
            outputs(m, [(0x90,84,100), (0x90,84,0)], route)
            assert m.get('lb_internal_held') == 0
    print('  [ok] real live trig-key on/off: eight tracks, EXT/INT/BOTH, DIN/USB')

    for track in range(8):
        for route in range(3):
            for param, msg in ((18,(0xe0,0,80)), (19,(0xd0,80))):
                for tail in (False, True):
                    m = prepare(track,route)
                    for t in range(8):
                        m.put(0x46c76dc0 + 68*t + 30, 1 << (param-18), 1)
                    other = (track+1)%8
                    m.put(0x8000000c, (255 ^ (1 << (other if tail else track))) << 8)
                    parent = 0x4005542c
                    m.call(0x4009eec8, (track,param,80,0), stop=parent, return_pc=parent)
                    outputs(m,[msg],route)
    print('  [ok] real cached/tail pitch bend and channel pressure: all tracks/routes')

    for track in range(8):
        for route in range(3):
            for banks in ((1, -1), (-1,2), (1,2)):
                m = prepare(track,route)
                for t in range(8):
                    m.put(0x40171442 + 36*t, 1 if t == track else 0, 1)
                base = 0x40171442+36*track
                m.put(base+1, banks[0]&255, 1)
                m.put(base+4, banks[1]&255, 1)
                m.put(base+2, 12, 1)
                m.call(0x4009ec70, (0,0))
                msgs = [(0xb0,cc,val) for cc,val in zip((0,32),banks) if val >= 0]
                msgs.append((0xc0,12))
                outputs(m,msgs,route)
    print('  [ok] real Part BANK/SBNK/PROG output, including six-byte bank pair')

    for route in range(3):
        m = prepare(0,route)
        for t in range(1,8):
            m.put(0x46c76de0+68*t,0,1)
        m.call(0x4009f288)
        outputs(m,[(0xb0,123,0)],route)
    print('  [ok] STOP panic follows track destinations')

    # The exact adapters called by the two frame-control sender operands.
    for site,msg in ((0x4009fdbe,(0xe0,0,64)),(0x4009fe2c,(0xd0,70))):
        for route in range(3):
            m=prepare(7,route)
            m.u.mem_write(MSG,bytes(msg))
            m.call(m.get(site+2),(len(msg),MSG),regs={UC_M68K_REG_D7:7},stop=site+6,return_pc=site+6)
            outputs(m,[msg],route)
    print('  [ok] installed frame bend/pressure operands route before DIN/USB')

    # Releases remain at their captured destinations after a route edit.
    for before in range(3):
        for after in range(3):
            m=prepare(3,before)
            m.call(0x4009e9a8,(3,84,100,0))
            m.call('lb_set_route',(3,after))
            m.call(0x4009e9a8,(3,84,0,0))
            assert m.get('lb_internal_held') == 0
            assert len(decode(bytes(m.u.mem_read(0x47005000-m.get(0x400b967c),m.get(0x400b967c)))[::-1])) == (0 if before == 1 else 2)
    print('  [ok] held live notes release at original destinations across every route edit')
    contexts()
    feedback()
    integration()


def contexts():
    m=prepare(4,0)
    # BANK/PROG belongs to the sender's bank/Part even when UI/playback differs.
    base=0x40171442+0x9b340+2*0x18b2+4*36
    for offset,value in ((0,2),(1,255),(2,7),(4,255),(12,4)):
        m.put(base+offset,value,1)
    m.call(0x4009ec70,(1,2))
    outputs(m,[(0xc1,7)],1)
    # A live key reads the UI Part while the sequencer stays in Part zero.
    m=prepare(4,0)
    m.put(0x100b14cf,1,1)
    base=0x40171442+0x18b2+4*36
    m.put(base,2,1);m.put(base+12,4,1)
    m.call(0x4009e9a8,(4,84,100,0));m.call(0x4009e9a8,(4,84,0,0))
    outputs(m,[(0x91,84,100),(0x91,84,0)],1)
    # Shared channel panic is a union, one CC per destination, not per track.
    m=prepare(0,1)
    m.call(0x4009f288)
    outputs(m,[(0xb0,123,0)],2)
    # A stray INT release cannot leak even without a previous owned note.
    m=prepare(0,1)
    m.u.mem_write(MSG,bytes((0x80,84,0)))
    m.call('lb_track_send',(3,MSG),regs={UC_M68K_REG_D7:0})
    outputs(m,[],1)
    print('  [ok] explicit bank/Part and UI/live contexts, shared-channel panic union, and unowned INT releases')


def feedback():
    for channel in (0,10):
        for msg in ((0x90,84,100),(0xb0,34,80),(0xc0,12),(0xd0,80),(0xe0,0,80),(0xa0,84,80)):
            packet=bytes((msg[0]|channel,*msg[1:]))
            for internal in (False,True):
                m=prepare(0,1)
                m.receiver_setup()
                m.put(0x46c82456,0x400e21e0)
                m.u.mem_write(0x8000003f,b'\xff'*8)
                m.put(0x80000012,1)
                m.put(0x80000000,0,1)
                m.put(0x100b14cc,0,1)
                if internal:
                    m.u.mem_write(MSG,packet)
                    m.call('lb_track_send',(len(packet),MSG),regs={UC_M68K_REG_D7:0})
                    delivered=m.next()
                    m.dispatch(delivered)
                else:m.dispatch(packet)
                n=m.get(0x400b967c)
                assert n==0 if internal else n+m.get(0x460d17ae+4)>0,(channel,msg,internal,n)
                if internal:
                    assert m.get(0x46c7fe4c+channel*4)==0,('receiver held leak',msg)
                    assert m.get(0x460d17ae+4)==0,('MIDI-track echo posted to main task',msg)
    print('  [ok] internal channel/auto messages cannot forward to DIN/USB or enqueue MIDI-track echoes; external input still forwards')


def integration():
    raw=subprocess.check_output(['m68k-elf-nm',str(ROOT/'out/platform/runtime/runtime.elf')],text=True)
    syms={n:int(a,16) for a,n in re.findall(r'^([0-9a-f]+) [Tt] (\w+)$',raw,re.M)}
    if 'bf_response_tick' in syms:
        from verify_midi_follow_response import fixture
        for track in range(8):
            for route in range(3):
                m=fixture(receiver=track,source=(track+1)%8)
                m.sym.update(syms)
                u=m.uc
                u.mem_write(Q,bytes(32))
                u.mem_write(Q+16,(255).to_bytes(4,'big'))
                u.mem_write(Q+20,(0x47002000).to_bytes(4,'big'))
                u.mem_write(syms['lb_routes']+track,bytes((route,)))
                u.mem_write(m.scratch,bytes((0x90+track,36,91)))
                m.call('lb_capture',regs={UC_M68K_REG_D0:0x4009fbb2,UC_M68K_REG_D1:track,
                    UC_M68K_REG_D2:3,UC_M68K_REG_A0:m.scratch})
                if route:m.call('lb_next')
                expected=[(0x90+track,36,0),(0x90+track,41,91)]
                assert m.change()==(expected if route!=1 else []),(track,route,m.events)
                if route:
                    for msg in expected:
                        ptr=m.call('lb_next')
                        assert tuple(u.mem_read(ptr,3))==msg
        print('  [ok] Follow LIVE real retriggers: all eight followers, internal packets and external suppression')
    if 'mh_owned_key' in syms:
        for route in range(3):
            m=prepare(2,route)
            m.sym.update(syms)
            for pitch in (60,64,67):m.call('mh_owned_key',(2,pitch,100,0))
            for pitch in (60,64,67):m.call('mh_owned_key',(2,pitch,0,0))
            outputs(m,[(0x90,p,100) for p in (60,64,67)]+[(0x90,p,0) for p in (60,64,67)],route)
            assert m.get('lb_internal_held')==0
        print('  [ok] Harmony generated live chord ownership reaches both routes with balanced releases')


if __name__ == '__main__':
    main()
