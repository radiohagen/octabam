#!/usr/bin/env python3
"""Execute the linked accumulator, independent boundary oracle and real file hooks.

The native filesystem boundary is substituted here, not the codec or saver.
Full-firmware panel/UART/card journeys live in the accompanying port gate.
"""
import json
import struct
import sys
from unicorn import UC_HOOK_CODE
from verify_harmony_degree_files import Files
from verify_harmony_track_retention import encode, header
from verify_harmony_degree_packed import oracle
from verify_harmony_degree_files import fnv
from unicorn.m68k_const import UC_M68K_REG_D7, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_D1, UC_M68K_REG_A0, UC_M68K_REG_A1
import harmony_retained as retained
from verify_harmony_degree_integration import symbols

BANK=0x400e21e0


def machine():
    """Harmony-only fixture; this gate must not require optional PLOCKS."""
    m=Files();u=m.uc
    m.call('ch_lock_init')
    u.mem_write(BANK,b'\xff'*0x9b340)
    for pattern in range(16):u.mem_write(BANK+pattern*0x8ed8+0x8e57,b'\0')
    for part in range(8):
        base=BANK+(0x8ed80+part*0x18b2 if part<4 else 0x9504a+(part-4)*0x18b2)
        for track in range(8):
            u.mem_write(base+0x3e2+track*32,b'\x30')
            for field,value in ((3,0),(5,2),(16,0),(17,1),(18,0),(19,35)):
                u.mem_write(base+0x4e2+track*36+field,bytes((value,)))
    m.call('hd_bank_loaded',0)
    return m


def main():
    m=machine();u=m.uc;s=m.sym
    if '--negative-control' in sys.argv:
        def no_advance(uc,pc,size,data):
            if pc==s['ha_sounded_c']:
                sp=uc.reg_read(UC_M68K_REG_A7)
                uc.reg_write(UC_M68K_REG_PC,int.from_bytes(uc.mem_read(sp,4),'big'))
                uc.reg_write(UC_M68K_REG_A7,sp+4)
        u.hook_add(UC_HOOK_CODE,no_advance)
    u.mem_write(0x46c82456,BANK.to_bytes(4,'big'))
    u.mem_write(0x100b14cc,b'\0');u.mem_write(0x100b14d0,b'\0')
    tones=(0,2,4,5,7,9,11)
    def pitch(offset):
        octave,degree=divmod(offset,7)
        return 48+12*octave+tones[degree]
    def setting(lo,hi,boundary=0,reset=3,base=1):
        m.c('ha_bank_reset_c',0);m.c('ha_runtime_reset_c')
        u.mem_write(s['ha_lanes']+32,bytes((lo&255,hi,boundary,reset,base)))
    def event(step=0,sound=True,repeats=1):
        m.c('ha_fire_c',0,0,0,step)
        value=m.c('ha_shift_c',48,0,0)
        if sound:
            for _ in range(repeats):m.c('ha_sounded_c',0)
        # A pool rebuild after output still uses this trig's captured offset.
        assert m.c('ha_shift_c',48,0,0)==value
        return value
    counts=0
    for mode in range(4):
        for lo,hi in ((0,0),(0,1),(-1,0),(-1,1),(-7,7),(-63,63)):
            for amount in (*range(-7,0),*range(1,8)):
                setting(lo,hi,mode)
                m.c('ha_set_c',0,0,0,0,amount+9 if amount<0 else amount+8)
                current=0;direction=1
                for _ in range(32):
                    result=event(repeats=4)
                    want=pitch(current)
                    assert result==(want if 0<=want<=127 else 0xffffffff),(mode,lo,hi,amount,current,result,want)
                    n=current+amount*direction
                    if lo==hi:n=lo
                    elif not lo<=n<=hi:
                        if mode==0:n=lo+(n-lo)%(hi-lo+1)
                        elif mode==1:
                            while not lo<=n<=hi:
                                n=2*hi-n if n>hi else 2*lo-n
                                direction=-direction
                        elif mode==2:n=max(lo,min(hi,n))
                        else:n=0
                    current=n;counts+=1
    print('[ok] independent boundary oracle:',counts,'outputs; arp repeats do not advance twice',flush=True)
    setting(0,7,base=9)
    assert event(sound=False)==48
    assert event()==48 and event()==50
    assert event(1)==48 and event(0)==52
    m.c('ha_set_c',0,0,0,0,1)
    assert event()==48 and event()==48
    m.c('ha_set_c',0,0,0,0,0)
    assert event()==48 and event()==50
    # START reads the incoming pattern policy; PAT and NONE have independent
    # contracts, and an unrelated step has its own phase/direction.
    setting(0,7,reset=1,base=9)
    assert event()==48 and event()==50
    m.c('ha_transport_c')
    assert event()==48
    setting(0,7,reset=0,base=9)
    assert event()==48 and event()==50
    m.c('ha_transport_c')
    assert event()==52
    for policy in range(4):
        setting(0,7,reset=policy,base=9)
        u.mem_write(s['ha_lanes']+8*37+32,bytes((0,7,0,policy,9)))
        assert event()==48 and event()==50
        m.c('ha_fire_c',0,1,0,0)
        assert m.c('ha_shift_c',48,0,0)==(48 if policy&2 else 52)
        m.c('ha_sounded_c',0)
        assert event()==(48 if policy&2 else 53)
        m.c('ha_transport_c')
        assert event()==(48 if policy&1 else 50 if policy&2 else 55)
    for hook,continuation in (('mp_start_a',0x4009c3da),('mp_start_b',0x4009c4da)):
        setting(0,7,reset=1,base=9)
        assert event()==48 and event()==50
        saved={UC_M68K_REG_D1:0x12345678,UC_M68K_REG_A0:m.scratch,UC_M68K_REG_A1:m.scratch+32}
        assert m.call(hook,1,stop=continuation,regs=saved)==1
        assert all(u.reg_read(reg)==value for reg,value in saved.items())
        assert u.reg_read(UC_M68K_REG_A7)==m.stack
        assert bytes(u.mem_read(0x800065b8,4))==b'\0\0\0\1'
        assert event()==48
    # Actual successful-send continuations: velocity zero and live arp pools
    # cannot consume a sequenced event. Register/stack ABI executes as linked.
    setting(0,7,base=9)
    m.c('ha_fire_c',0,0,0,0)
    u.mem_write(0x46c77b1e,b'\0');u.mem_write(0x400d807c,b'\x90\x30\0')
    m.call('mp_sent_a',stop=0x4009fbb8,regs={UC_M68K_REG_D7:0})
    assert event(sound=False)==48
    u.mem_write(0x400d807e,b'\x64');u.mem_write(0x46c77b1e,b'\1')
    m.call('mp_sent_b',stop=0x4009fd00,regs={UC_M68K_REG_D7:0})
    assert event(sound=False)==48
    u.mem_write(0x46c77b1e,b'\0')
    m.call('mp_sent_a',stop=0x4009fbb8,regs={UC_M68K_REG_D7:0})
    assert event(sound=False)==50
    print('[ok] inherited/OFF, silent occurrences, reset policies and successful-send guards',flush=True)
    # All 16 states survive a dense same-step checkpoint, including OFF.
    expected=bytearray()
    for lane in range(128):
        row=bytes(((2*i+lane)%16<<4)|((2*i+lane+1)%16) for i in range(32))
        row+=bytes(((-lane%64)&255, lane%64, lane%4, (lane//4)%4,1+lane%15))
        # lower is a signed non-positive byte, independently from upper.
        row=row[:32]+bytes(((-(lane%64))&255,))+row[33:]
        expected.extend(row)
    u.mem_write(s['ha_lanes'],bytes(expected))
    m.c('hd_nv_save_c',0)
    roots=bytes(u.mem_read(s['hd_banks'],16768));q=bytes(u.mem_read(s['ch_lock_table'],8192))
    payload=oracle(roots,q)+expected
    snap=retained.snapshot(m);h=header(snap)
    assert snap==encode(payload,0,int.from_bytes(h[3:7],'big'),h[2])
    u.mem_write(s['ha_lanes'],b'\xcc'*4736)
    assert m.c('hd_nv_restore_c',0)==1
    assert bytes(u.mem_read(s['ha_lanes'],4736))==expected
    # Valid checksums cannot admit malformed settings, even in the last lane.
    for offset,value in ((32,1),(32,192),(33,64),(34,4),(35,4),(36,0)):
        corrupt=bytearray(payload);corrupt[10368+127*37+offset]=value
        retained.install(m,encode(corrupt))
        assert m.c('hd_nv_restore_c',0)==0
        assert bytes(u.mem_read(s['ha_lanes'],4736))==expected
    retained.install(m,snap)
    print('[ok] 8192 ACC nibbles and all settings: physical mapping, dense restore, corrupt-config rejection',flush=True)
    assert m.call('ch_file_write',0)==1
    path='/SET/PROJECT/hdeg01.work';new=m.files[path]
    assert new[:8]==b'HDP4\0\0\0\4' and len(new)==15136
    m.c('ha_bank_reset_c',0);m.call('ch_file_read',0)
    assert bytes(u.mem_read(s['ha_lanes'],4736))==expected
    old_payload=new[32:32+10368]
    old=struct.pack('>8I',0x48445033,3,0,10368,fnv(old_payload),int.from_bytes(new[20:24],'big'),0,0)+old_payload
    m.files[path]=old;m.call('ch_file_read',0)
    assert u.mem_read(s['ch_lock_status'],1)==b'\2'
    assert m.call('ch_file_write',0)==0xfffffff9 and m.files[path]==old
    m.files[path]=new;m.call('ch_file_read',0)
    assert bytes(u.mem_read(s['ha_lanes'],4736))==expected
    assert bytes(u.mem_read(s['ch_lock_table'],8192))==q
    print('[ok] HDP4 round trip; obsolete HDP3 rejected and protected from overwrite',flush=True)
    legacy=bytearray()
    for lane in range(128):
        row=old_payload[lane*81:(lane+1)*81]
        hdr=bytes((1,0,lane,row[0],1,0,0,0))+(17).to_bytes(4,'big')
        hdr+=fnv(hdr+row).to_bytes(4,'big')
        meta=int.from_bytes(hdr,'big')<<4
        tokens=int.from_bytes(row[1:],'big')
        for step in range(64):
            top=43 if step==0 else (meta>>(6*(22-step)))&63 if step<=22 else 0
            legacy.extend(((top<<10)|((tokens>>(10*(63-step)))&1023)).to_bytes(2,'big'))
    retained.install(m,legacy);u.mem_write(s['ha_lanes'],bytes(expected))
    assert m.c('hd_nv_restore_c',0)==0
    assert bytes(u.mem_read(s['ha_lanes'],4736))==expected
    assert bytes(u.mem_read(s['ch_lock_table'],8192))==q
    print('[ok] obsolete HMT1 checkpoint rejected without publication',flush=True)
    # Carry actual musical config through the existing native memcpy bridge.
    u.mem_write(s['ha_lanes'],bytes(expected))
    for dst,src,length in ((BANK+0x8ed8+0x48d0,BANK+0x48d0,0x8b0),
                           (0x460c8122,BANK,0x8ed8),
                           (BANK+2*0x8ed8,0x460c8122,0x8ed8)):
        m.c('ch_memcpy',dst,src,length)
    assert bytes(u.mem_read(s['ha_lanes']+8*37,37))==expected[:37]
    assert bytes(u.mem_read(s['ha_lanes']+16*37,8*37))==expected[:8*37]
    before=bytes(u.mem_read(s['ha_lanes'],4736))
    m.c('hd_forget_c',0,0,0,3)
    cleared=bytearray(before);cleared[1]&=0xf0
    assert bytes(u.mem_read(s['ha_lanes'],4736))==cleared
    print('[ok] native track/pattern clipboard bridge carries ACC; step clear is scoped',flush=True)
    result=dict(boundary_outputs=counts,dense_steps=8192,obsolete_formats_rejected=True,hardware_tested=False)
    out=__import__('pathlib').Path(__file__).resolve().parents[2]/'out/harmony-accumulator'
    out.mkdir(parents=True,exist_ok=True);(out/'linked.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
