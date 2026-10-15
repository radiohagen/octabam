"""Execute STORE with each original client combination, without Harmony or an OS."""
import itertools
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import toolpath
from remix.registry import _load_one
try:
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    from unicorn.m68k_const import *
except ImportError:
    Uc=None


@unittest.skipUnless(Uc and shutil.which('m68k-elf-as'), 'ColdFire assembler and Unicorn required')
class StoreCopyClients(unittest.TestCase):
    def test_original_clients_after_native_success_and_failure(self):
        module=_load_one(ROOT/'modules/store/manifest.py')
        with tempfile.TemporaryDirectory() as directory:
            work=pathlib.Path(directory)
            (work/'layout.ld').write_text('SECTIONS { . = 0x48000000; .text : { *(.text*) } .data : { *(.data*) } .bss : { *(.bss*) } }')
            for bits in itertools.product((False,True),repeat=3):
                names={name for name,active in zip(('PLOCKS P2','KITS','MIDI SCENES'),bits) if active}
                with self.subTest(clients=sorted(names)):
                    (work/'remix.inc').write_text(module.linked[0].include(names))
                    subprocess.run(['m68k-elf-as','-mcpu=54455','-I',str(work),'-o',str(work/'store.o'),str(ROOT/'modules/store/store.s')],check=True,capture_output=True)
                    undefined=subprocess.check_output(['m68k-elf-nm','-u',str(work/'store.o')],text=True)
                    stubs={line.split()[-1]:0x47010000+i*16 for i,line in enumerate(undefined.splitlines())}
                    defs=[f'--defsym={name}={address}' for name,address in stubs.items()]
                    subprocess.run(['m68k-elf-ld','-T',str(work/'layout.ld'),*defs,'-o',str(work/'store.elf'),str(work/'store.o')],check=True,capture_output=True)
                    subprocess.run(['m68k-elf-objcopy','-O','binary',str(work/'store.elf'),str(work/'store.bin')],check=True)
                    nm=subprocess.check_output(['m68k-elf-nm',str(work/'store.elf')],text=True)
                    sym={f[2]:int(f[0],16) for f in (line.split() for line in nm.splitlines()) if len(f)==3}
                    for optional in ('fire_checked','NP_RET','ev_bankw_guard',
                                     'ev_bankcopy_guard','ev_bankcopy_done','ev_newproj_post'):
                        self.assertNotIn(optional,sym)
                    u=Uc(UC_ARCH_M68K,UC_MODE_BIG_ENDIAN);u.ctl_set_cpu_model(UC_CPU_M68K_CFV4E)
                    for address in (0x40000000,0x47000000,0x48000000):u.mem_map(address,0x20000)
                    u.mem_write(0x48000000,(work/'store.bin').read_bytes())
                    native=0x40016388;done=0x4701fff0;stack=0x47008000
                    for address in (native,done,*stubs.values()):u.mem_write(address,b'\x4e\x75')
                    calls=[];result=0
                    def io(u,pc,size,data):
                        if pc==done:u.emu_stop();return
                        if pc!=native and pc not in stubs.values():return
                        sp=u.reg_read(UC_M68K_REG_A7);ret=int.from_bytes(u.mem_read(sp,4),'big')
                        if pc==native:
                            calls.append(('native',struct.unpack('>3I',u.mem_read(sp+4,12))))
                            value=result
                        else:
                            calls.append(('client',(u.reg_read(UC_M68K_REG_D0),u.reg_read(UC_M68K_REG_D1))))
                            for r in (*range(UC_M68K_REG_D0,UC_M68K_REG_D7+1),*range(UC_M68K_REG_A0,UC_M68K_REG_A6+1)):
                                u.reg_write(r,0xdeadbeef)
                            value=0
                        u.reg_write(UC_M68K_REG_D0,value&0xffffffff)
                        u.reg_write(UC_M68K_REG_A7,sp+4);u.reg_write(UC_M68K_REG_PC,ret)
                    u.hook_add(UC_HOOK_CODE,io)
                    for result in (-12,0,1):
                        calls.clear();u.reg_write(UC_M68K_REG_SR,0x2700);u.reg_write(UC_M68K_REG_A7,stack)
                        u.reg_write(UC_M68K_REG_D2,0x1234);u.reg_write(UC_M68K_REG_A2,0x5678)
                        u.mem_write(stack,struct.pack('>4I',done,0x1111,0x2222,0))
                        u.emu_start(sym['store_fcopy'],0,count=10000)
                        expected=[('native',(0x1111,0x2222,0))]
                        if result>=0 and 'PLOCKS P2' in names:expected.append(('client',(0x1111,0x2222)))
                        self.assertEqual(calls,expected)
                        self.assertEqual(u.reg_read(UC_M68K_REG_D0),result&0xffffffff)
                        self.assertEqual(u.reg_read(UC_M68K_REG_A7),stack+4)
                        self.assertEqual(u.reg_read(UC_M68K_REG_PC),done)
                        self.assertEqual(u.reg_read(UC_M68K_REG_D2),0x1234)
                        self.assertEqual(u.reg_read(UC_M68K_REG_A2),0x5678)


if __name__=='__main__':unittest.main()
