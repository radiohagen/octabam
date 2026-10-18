#!/usr/bin/env python3
"""Linked client/STORE ABI with injected native file-I/O outcomes.

This deliberately models only the file service. Native virtual-card save/load
is a separate port gate; this gate covers deterministic fault injection.
"""
import struct
import zlib
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_PC
from verify_midi_loopback_translation import machine, set_config, send, drain

B, BS, PS = 0x400e21e0, 0x9b340, 0x18b2
WORK, SAVED = B+0x8ed80, B+0x9504a
TEXT = 0x47001100


class Files:
    def __init__(self, m):
        self.m=m;self.files={};self.open={};self.calls=[];self.fail=None
        self.project='/SET/PROJECT'
        m.put(0x46c823fa,0x4700ffe0)
        m.u.hook_add(UC_HOOK_CODE,self.service)

    def string(self,at):
        return bytes(self.m.u.mem_read(at,260)).split(b'\0')[0].decode()

    def service(self,u,pc,size,data):
        if pc not in (0x40025230,0x4700ffe0,0x40016864,0x40016564,
                      0x400166b8,0x4001677c,0x400148d4,0x40016388): return
        m=self.m;sp=u.reg_read(UC_M68K_REG_A7)
        args=[m.get(sp+4+4*i) for i in range(5)]
        self.calls.append(pc);result=0
        if pc==0x40025230:
            u.mem_write(TEXT,self.project.encode()+b'\0');result=TEXT
        elif pc==0x4700ffe0: result=int(self.string(args[0]) in self.files)
        elif pc==0x40016864:
            ctx,path,mode,buffer,length=args
            path=self.string(path);mode=self.string(mode)
            if '/lbnt' in path: assert buffer==ctx+24 and length==4096
            if self.fail=='open' or (mode=='r' and path not in self.files): result=-7
            else:
                self.open[ctx]=(path,mode)
                if mode=='w': self.files[path]=b''
        elif pc==0x400148d4: result=len(self.files[self.open[args[0]][0]])
        elif pc in (0x40016564,0x400166b8):
            ctx,buffer,length=args[:3];path,mode=self.open[ctx]
            if pc==0x40016564:
                assert mode=='r'
                result=int(self.fail!='read' and len(self.files[path])==length)
                if result: u.mem_write(buffer,self.files[path])
            else:
                assert mode=='w'
                result=int(self.fail!='write')
                self.files[path]=bytes(u.mem_read(buffer,length if result else 11))
        elif pc==0x4001677c:
            del self.open[args[0]];result=-7 if self.fail=='close' else 0
        elif pc==0x40016388:
            dst,src=map(self.string,args[:2])
            if self.fail=='copy' or src not in self.files: result=-7
            else: self.files[dst]=self.files[src]
        u.reg_write(UC_M68K_REG_D0,result&0xffffffff)
        u.reg_write(UC_M68K_REG_PC,m.get(sp));u.reg_write(UC_M68K_REG_A7,sp+4)

    def path(self,bank=0,extension='work'):
        return f'{self.project}/lbnt{bank+1:02}.{extension}'


def strings(m,*values):
    result=[]
    for i,v in enumerate(values):
        at=TEXT+260*(i+1);m.u.mem_write(at,v.encode()+b'\0');result.append(at)
    return result


def main():
    m=machine();f=Files(m)
    m.call('lt_load_banks',(65535,))
    assert m.call('lt_save_banks',(65535,))==0 and not f.files
    assert m.call('lt_get',(63,7,0))==0 and m.call('lt_get',(63,7,1))==60
    assert m.get('lt_readonly')==0
    # All 512 independent settings, actual native Part copy to saved records.
    for bank in range(16):
        for part in range(4):
            for track in range(8):
                set_config(m,1+(track%3),source=40+part,target=80+bank,track=track,context=4*bank+part)
            m.call('mp_native_copy',(SAVED+bank*BS+part*PS,WORK+bank*BS+part*PS,PS))
    assert m.get(B+0x9b332)==1 and m.get(B+15*BS+0x95048,1)==15
    expected=bytes(m.u.mem_read(m.sym['lt_work'],2560))
    assert bytes(m.u.mem_read(m.sym['lt_saved'],2560))==expected
    assert m.call('lt_save_banks',(65535,))==0
    assert len(f.files)==16
    for bank in range(16):
        data=f.files[f.path(bank)]
        assert len(data)==336
        assert struct.unpack('>III',data[:12])==(0x4c424e54,1,320)
        assert int.from_bytes(data[12:16],'big')==zlib.crc32(data[16:])
        assert data[16:176]==data[176:]==expected[bank*160:(bank+1)*160]
    m.call('lt_new_project');assert not any(m.u.mem_read(m.sym['lt_work'],2560))
    m.call('lt_load_banks',(65535,))
    assert bytes(m.u.mem_read(m.sym['lt_work'],2560))==expected
    assert bytes(m.u.mem_read(m.sym['lt_saved'],2560))==expected
    # Native Part clipboard/save/reload/clear preserve separate working/saved values.
    m.call('lt_new_project')
    before=len(f.calls)
    m.call('lt_st_fromcs1',regs={UC_M68K_REG_D0:0})
    assert len(f.calls)==before,'early retained-state restore performed filesystem I/O'
    m.call('lt_st_loadmask_post',regs={UC_M68K_REG_D1:2})
    assert bytes(m.u.mem_read(m.sym['lt_work'],320))==expected[:320]
    m.call('lt_load_banks',(65535,))
    set_config(m,3,source=61)
    m.call('mp_native_copy',(0x460bf218,WORK,PS))
    m.call('mp_native_copy',(WORK+PS,0x460bf218,PS))
    assert m.call('lt_get',(1,0,1))==61
    m.call('mp_native_copy',(WORK,SAVED,PS))
    assert m.call('lt_get',(0,0,1))==40
    m.call('lt_part_init',(WORK+PS,))
    assert m.call('lt_get',(1,0,0))==0 and m.call('lt_get',(1,0,1))==60
    print('[ok] absent files stay OFF; 512 per-bank/Part/track records round-trip with native Part copies and CRC',flush=True)

    good=f.files[f.path()]
    damaged=[]
    for at,value in ((0,0),(7,2),(11,0),(12,0),(16,9),(19,64),(19,127)):
        blob=bytearray(good);blob[at]=value
        if at>=16: blob[12:16]=zlib.crc32(blob[16:]).to_bytes(4,'big')
        damaged.append(bytes(blob))
    damaged.extend((good[:-1],good+b'\0'))
    for blob in damaged:
        f.files[f.path()]=blob;m.call('lt_load_banks',(1,))
        assert m.get('lt_readonly')&1 and m.call('lt_get',(0,0,0))==0
        assert m.call('lt_set',(0,0,0,1))==0
        assert m.call('lt_save_banks',(1,))==0xfffffff9
        assert f.files[f.path()]==blob
    # Registry bank argument is zero-based (the dialog adds one).
    pend=m.sym['store_pend'];assert bytes(m.u.mem_read(pend,2))==bytes((3,0))
    m.call('store_answer_cb',(2,0))
    assert not m.get('lt_readonly')&1
    assert m.call('lt_save_banks',(1,))==0
    assert f.files[f.path(extension='bak')]==damaged[-1]
    assert not any(f.files[f.path()][16:])
    print('[ok] bad length/magic/version/CRC/record refuses edits and writes; explicit STORE backup preserves the original',flush=True)

    for failure in ('open','write','close'):
        m=machine();f=Files(m);set_config(m,3);f.fail=failure
        assert m.call('lt_save_banks',(1,))==0xfffffff9
        src,=strings(m,f.project+'/bank01.work')
        assert m.call('lt_copy_guard',(src,))==0xfffffff9
        f.fail=None;assert m.call('lt_save_banks',(1,))==0
        assert m.call('lt_copy_guard',(src,))==0
    # Actual STORE copy wrapper, not just client callbacks: both failure sides.
    dst,src=strings(m,f.project+'/bank01.strd',f.project+'/bank01.work')
    f.files[f.project+'/bank01.work']=b'native bank sentinel'
    assert m.call('store_fcopy',(dst,src,0))==0
    assert f.files[f.path(extension='strd')]==f.files[f.path()]
    before=dict(f.files);f.fail='copy'
    assert m.call('store_fcopy',(dst,src,0))==0xfffffff9 and f.files==before
    f.fail=None
    del f.files[f.path()]
    assert m.call('store_fcopy',(dst,src,0))==0
    assert not any(f.files[f.path(extension='strd')][16:])
    print('[ok] open/write/close errors block stored-backup promotion; native copy failure does not advance companion state',flush=True)

    # Loading another project releases translated identities, not the new map.
    m=machine();f=Files(m);set_config(m,3);send(m,(0x90,60,100));drain(m)
    f.project='/SET/OTHER';m.call('lt_load_banks',(65535,))
    assert drain(m)==[[0x80,84,0]] and m.call('lt_get',(0,0,0))==0
    send(m,(0x80,60,0),pc=0x4009f8c2);assert not drain(m)
    print('[ok] project load releases old translated held notes and leaves missing-file defaults OFF',flush=True)


if __name__=='__main__': main()
