#!/usr/bin/env python3
"""Opt-in linked ColdFire instruction benchmarks, never hardware cycle claims.

Build a MIDI remix first. --artifacts accepts a frozen out/ layout so the
same fixtures can compare the exact baseline and candidate firmware bytes.
--compare refuses changed result digests; normal verification remains separate.
"""
import argparse
import bisect
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import *
from midi_machine import Machine, ROOT, InterruptMaskTrace

BANK, STRIDE = 0x400e21e0, 0x9b340


class CpuMachine(Machine):
    def __init__(self, out):
        nm = subprocess.check_output(['m68k-elf-nm',str(out/'platform/runtime/runtime.elf')],text=True)
        rows = [line.split() for line in nm.splitlines()]
        symbols = {f[2]:int(f[0],16) for f in rows if len(f)==3}
        self.labels = sorted((int(f[0],16),f[2]) for f in rows if len(f)==3 and f[1] in ('T','t'))
        self.addresses = [a for a,_ in self.labels]
        super().__init__(lambda:symbols,artifact_root=out)
        self.initial_sr = 0x2000
        self.call('mp_activate',stop=0x4000f938)
        self.call('ch_lock_init')
        self.uc.mem_write(BANK,b'\xff'*STRIDE)
        for pattern in range(16): self.put(BANK+pattern*0x8ed8+0x8e57,0)
        for part in range(8):
            base = BANK+(0x8ed80+part*0x18b2 if part<4 else 0x9504a+(part-4)*0x18b2)
            self.uc.mem_write(base+0x1712,bytes(288))
            for t in range(8):
                self.put(base+0x3e2+t*32,60)
                for field,value in ((3,0),(5,0),(12,0),(13,3),(15,2),(16,0),(17,1),(18,0),(19,42)):
                    self.put(base+0x4e2+t*36+field,value)
        for t in range(8):
            self.put(0x46c76df1+68*t,1)
            self.put(0x46c76fe0+32*t,60)
            self.put(0x46c76fec+32*t,64)
            self.put(0x8000182a+t,0); self.put(0x80001832+t,0)
        self.put(0x80001828,0); self.put(0x80001829,0)
        self.call('hd_bank_loaded',0)

    def put(self,address,value,n=1): self.uc.mem_write(address,(value&((1<<(n*8))-1)).to_bytes(n,'big'))
    def c(self,name,*args):
        self.uc.mem_write(self.stack+4,b''.join((v&0xffffffff).to_bytes(4,'big') for v in args))
        result=self.call(name)
        assert self.uc.reg_read(UC_M68K_REG_A7)==self.stack+4,name
        return result
    def mode(self,value):
        for t in range(8): self.put(self.part_address(t,5),value)
    def instruction_limit(self,name): return 30000000
    def profile(self,run):
        counts=Counter(); trace=InterruptMaskTrace(self.uc,ipl=0)
        masked=peak=0
        def count(u,pc,size,user):
            nonlocal masked,peak
            if pc in self.stops:return
            counts[pc]+=1
            old=trace.before(pc)
            if old or trace.ipl: masked+=1; peak=max(peak,masked)
            else: masked=0
        hook=self.uc.hook_add(UC_HOOK_CODE,count)
        try: result=run()
        finally: self.uc.hook_del(hook)
        by_name=Counter()
        for pc,n in counts.items():
            i=bisect.bisect_right(self.addresses,pc)-1
            name=self.labels[i][1] if i>=0 and pc>=self.base else 'native'
            by_name[name]+=n
        encoded=json.dumps(result,sort_keys=True,separators=(',',':')).encode()
        return sum(counts.values()),peak,hashlib.sha256(encoded).hexdigest(),by_name.most_common(8)


def cases(m):
    u,s=m.uc,m.sym
    yield 'part/read_8_tracks',lambda:[m.call('mp_read',t,0,regs={UC_M68K_REG_D2:5}) for t in range(8)]
    yield 'follow/no_routes_8_tracks',lambda:[m.call('bf_source_resolve',t) for t in range(8)]
    m.follow_write('source',bytes((2,3,4,5,6,7,8,0)))
    yield 'follow/chain_8_tracks',lambda:[m.call('bf_source_resolve',t) for t in range(8)]
    m.follow_write('source',bytes(8))
    yield 'follow/trig_first_tick',lambda:m.call('bf_response_tick')
    yield 'follow/trig_steady_tick',lambda:m.call('bf_response_tick')
    m.follow_write('response',bytes([1]*8))
    yield 'follow/live_first_tick',lambda:m.call('bf_response_tick')
    yield 'follow/live_steady_tick',lambda:m.call('bf_response_tick')
    m.follow_write('source',bytes((0,1,1,1,1,1,1,1)))
    u.mem_write(s['bf_roots'],bytes([48]*8));u.mem_write(s['bf_pitches'],bytes([60]*8))
    yield 'follow/live_target_8_tracks',lambda:[m.call('bf_response_target',t) for t in range(8)]
    m.follow_write('source',bytes(8))
    m.follow_write('response',bytes(8))
    for raw in (0,1,24,25,84,255):
        yield f'scales/decode_{raw}',lambda raw=raw:m.call('ms_decode',raw)
    for raw in (0,1,84):
        yield f'scales/snap_{raw}_128_notes',lambda raw=raw:[m.call('ms_snap',n,raw) for n in range(128)]
    for scale in (0,320,428):
        yield f'harmony/decode_{scale}_84_degrees',lambda scale=scale:[m.call('hd_decode',d,scale) for d in range(84)]
        yield f'harmony/encode_{scale}_128_notes',lambda scale=scale:[m.call('hd_encode',n,scale) for n in range(128)]
    for mode in (0,1,2):
        m.mode(mode)
        for t in range(8): m.c('hd_sync_c',0,0,t)
        yield f'harmony/stage_mode_{mode}_8_tracks',lambda:[m.c('hd_event_stage_c',0,0,t,0,0) and 0 for t in range(8)]
        for t in range(8):m.c('hd_event_fire_c',t,t)
        yield f'harmony/tick_mode_{mode}_8_tracks',lambda:[m.c('hd_event_tick_c',t) and 0 for t in range(8)]
        yield f'harmony/prepare_mode_{mode}_8_tracks',lambda:[m.c('hd_prepare_c',60,t) for t in range(8)]
        def generate():
            result=[]
            for t in range(8):
                u.mem_write(m.scratch,bytes((60,11,12,13)))
                m.call('mh_generate',t,0,a0=m.scratch)
                result.append(bytes(u.mem_read(m.scratch,4)).hex())
            return result
        yield f'harmony/generate_mode_{mode}_8_tracks',generate
    m.mode(2)
    for auto in (0,1):
        m.call('mh_voic_set',0,auto)
        def progression():
            result=[]
            for pitches in ((60,64,67,60),(62,65,69,62),(67,71,74,67),(60,64,67,60)):
                u.mem_write(m.scratch,bytes(pitches));m.call('mh_voice',0,a0=m.scratch)
                result.append(bytes(u.mem_read(m.scratch,4)).hex())
            return result
        yield f'harmony/voicing_{auto}_4_chords',progression
    # Initialized OFF, sparse HARM and fully locked HARM current banks.
    for name,density in (('empty',0),('sparse',8),('dense',8192)):
        roots=bytearray();qualities=bytearray()
        for lane in range(128):
            degrees=[(lane*64+i)%84 if lane*64+i<density else 255 for i in range(64)]
            notes=[255 if d==255 else max(0,min(127,(d//7-1)*12+(0,2,4,5,7,9,11)[d%7])) for d in degrees]
            roots.extend(bytes(degrees+notes+[2 if density else 1,0,255]))
            qualities.extend(bytes((i+lane)%8 if lane*64+i<density else 255 for i in range(64)))
        u.mem_write(s['hd_banks'],bytes(roots));u.mem_write(s['ch_lock_table'],bytes(qualities))
        def retain():
            m.call('ch_nv_save',0)
            return bytes(u.mem_read(0x100fd560,10400)).hex()
        yield f'harmony/retain_{name}',retain


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--artifacts',type=Path,default=ROOT/'out')
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--compare',type=Path)
    ap.add_argument('--repeat',type=int,default=2)
    a=ap.parse_args(); assert a.repeat>0
    samples={}
    for repeat in range(a.repeat):
        m=CpuMachine(a.artifacts)
        for name,run in cases(m):
            record=m.profile(run); samples.setdefault(name,[]).append(record)
            if repeat==0:print(f'{name:43} {record[0]:>10,} instructions  {record[1]:>7,} max masked',flush=True)
    report={'measurement':'executed ColdFire instructions; not cycles or hardware timing',
            'image_sha256':hashlib.sha256((a.artifacts/'mainos_bus.bin').read_bytes()).hexdigest(),
            'fixture_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'repeat':a.repeat,'cases':{}}
    previous=json.loads(a.compare.read_text())['cases'] if a.compare else None
    for name,rows in samples.items():
        assert len({(n,p,h) for n,p,h,_ in rows})==1,('nondeterministic fixture',name,rows)
        n,peak,digest,hot=rows[0]
        value={'instructions':n,'max_masked':peak,'result_sha256':digest,'hotspots':hot}
        if previous:
            assert previous[name]['result_sha256']==digest,('behavior changed',name)
            value['baseline_instructions']=previous[name]['instructions']
            value['ratio']=n/previous[name]['instructions']
        report['cases'][name]=value
    if previous: assert set(previous)==set(samples),'benchmark case set changed'
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(f'Wrote {a.output}',flush=True)


if __name__=='__main__':main()
