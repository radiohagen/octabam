#!/usr/bin/env python3
"""STORE copy notifications follow native success; failures leave clients alone."""
import json
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import *
from midi_machine import Machine, ROOT


def symbols():
    raw=subprocess.check_output(['m68k-elf-nm',str(ROOT/'out/platform/runtime/runtime.elf')],text=True)
    return {f[2]:int(f[0],16) for f in (line.split() for line in raw.splitlines()) if len(f)==3}


def main():
    m=Machine(symbol_loader=symbols);u=m.uc
    handlers={address:name for name,address in m.sym.items()
              if name.endswith(('_st_bankcopy','_st_bankcopy_guard','_st_bankcopy_done'))}
    native=[];clients=[];result=0;dst=m.scratch;src=m.scratch+260
    u.mem_write(dst,b'/SET/PROJECT/bank01.strd\0');u.mem_write(src,b'/SET/PROJECT/bank01.work\0')
    def io(u,pc,size,data):
        if pc!=0x40016388 and pc not in handlers:return
        sp=u.reg_read(UC_M68K_REG_A7);ret=int.from_bytes(u.mem_read(sp,4),'big')
        if pc==0x40016388:
            native.append(struct.unpack('>3I',u.mem_read(sp+4,12)));value=result
        else:
            name=handlers[pc]
            clients.append((name,u.reg_read(UC_M68K_REG_D0),u.reg_read(UC_M68K_REG_D1)))
            value=0
            for r in (*range(UC_M68K_REG_D0,UC_M68K_REG_D7+1),*range(UC_M68K_REG_A0,UC_M68K_REG_A6+1)):
                u.reg_write(r,0xabcddcba)
        u.reg_write(UC_M68K_REG_D0,value&0xffffffff)
        u.reg_write(UC_M68K_REG_A7,sp+4);u.reg_write(UC_M68K_REG_PC,ret)
    u.hook_add(UC_HOOK_CODE,io)
    for result in (-12,0,1):
        native.clear();clients.clear()
        u.mem_write(m.stack+4,struct.pack('>3I',dst,src,0))
        actual=m.call('store_fcopy')
        assert actual==result&0xffffffff,(result,actual)
        assert native==[(dst,src,0)],native
        expected={name for name in handlers.values() if result>=0 or name.endswith('_guard')}
        assert {name for name,_,_ in clients}==expected,(result,clients,expected)
        assert len(clients)==len(expected)
        assert all((d,s)==(dst,src) for _,d,s in clients)
        assert u.reg_read(UC_M68K_REG_A7)==m.stack+4
    report={'native_copy_results':[-12,0,1],'native_copy_once':True,
            'failure_skips_all_companion_notifications':True,'callback_arguments_preserved':True}
    path=ROOT/'out/store-copy.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
