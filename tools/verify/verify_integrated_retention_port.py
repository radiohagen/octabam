#!/usr/bin/env python3
"""All three maximum-capacity unsaved stores through the full firmware.

Seed independently encoded battery SRAM, resume without LOAD PROJECT,
checkpoint with the real native bank-copy path, and resume that result.
No physical device or user project is written.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import verify_midi_harmony_port as port
from verify_midi_sram import BASE, OFFSETS, B, SIZE, symbols
from verify_plocksp2_retention import rice
from midi_machine import ROOT


def fnv(data):
    h=0x811c9dc5
    for byte in data:h=((h^byte)*0x1000193)&0xffffffff
    return h


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--project',required=True,type=Path)
    ap.add_argument('--candidate',type=Path,help='frozen directory with candidate.bin and candidate-all-symbols.json')
    ap.add_argument('--legacy',action='store_true',help='migrate the H8 P2/Harmony checkpoints and Part scene blobs')
    args=ap.parse_args();port.OUT=ROOT/('out/integrated-retention-legacy' if args.legacy else 'out/integrated-retention');port.OUT.mkdir(parents=True,exist_ok=True)
    w=port.fixture(args.project,'dense',{i:2 for i in range(8)},first_note=48)
    if args.candidate:
        image=args.candidate/'candidate.bin'
        sym=json.loads((args.candidate/'candidate-all-symbols.json').read_text())
    else:
        image=port.freeze_candidate(port.OUT);sym=symbols()
    assert sym['hd_nv_base']==0x100f8620 and 'plk_pool_encode' in sym
    port.run(w,'base',['--sequencer','--internal-clock','--frames','1','--mem-dump',f'0x10000000,0x100000={w}/base-cs1.bin'],image=image)
    seed=bytearray((w/'base-cs1.bin').read_bytes())
    # 10,234 P2 locks with worst-bound Rice gap placement, including a long
    # leading run. This is the legacy capacity, not upstream's reduced cap.
    count=10234;gaps=[8]*count;gaps[0]+=8*((98304-count)//8-count)
    records=[];index=-1;expected_p2=bytearray(b'\xff'*98304)
    for i,gap in enumerate(gaps):
        index+=gap+1;value=i%128;records.append((index,value));expected_p2[index]=value
    encoded=rice(records,bank=0);assert len(encoded)<=15464
    seed[0xf8600:0xf8614]=b'P2S1'+encoded[:16]
    for off,value in zip(OFFSETS,encoded[16:]):seed[BASE-0x10000000+off]=value
    # Every MIDI step has a root and an explicit chord quality, including
    # canonical NOTE clipping at both ends. Four 10-bit tokens are five bytes.
    payload=bytearray();degrees=bytearray();qualities=bytearray()
    tones=(0,2,4,5,7,9,11)
    for lane in range(128):
        payload.append(168) # HARM state, scale 0
        bits=0
        for step in range(64):
            d=(lane+step)%84;q=(lane*3+step)%8
            degrees.append(d);qualities.append(q);bits=(bits<<10)|(d*9+q)
            at=BASE-0x10000000+(lane//8)*0x8ed8+0x4900+(lane%8)*0x8b0+step*32
            seed[at]=max(0,min(127,12*(d//7-1)+tones[d%7]))
        payload.extend(bits.to_bytes(80,'big'))
    header=struct.pack('>8I',0x48444e33,3,0,len(payload),fnv(payload),1,1,0xfffffffe)
    seed[0xf8620:0xf8620+10400]=header+payload
    # Fill all 4096 bytes in each of four Scene tables; no sparse shortcut.
    scenes=bytes((i*11+(i//4096)*17)%84 for i in range(16384))
    checksum=sum(struct.unpack('>4096I',scenes))&0xffffffff
    seed[0xfbdf0:0xfbe00]=struct.pack('>4I',0x53435331,0,checksum,0)
    seed[0xfbe00:0xffe00]=scenes
    (w/'dense-cs1.bin').write_bytes(seed)
    # Guards in the remaining dedicated region catch accidental legacy writes.
    guard_start=0xfaec0;guard_end=0xfbdf0
    seed[guard_start:guard_end]=b'\xa5'*(guard_end-guard_start)
    if args.legacy:
        seed[0xf8600:0xffe00]=b'\xff'*(0xffe00-0xf8600)
        seed[0xf8600:0xf8600+len(encoded)]=encoded
        seed[0xfd560:0xffe00]=header+payload
        scenes=bytearray(b'\xff'*16384)
        for part in range(4):
            records=[(scene*256+t*32,(part*17+scene*7+t)%84) for scene in range(2) for t in range(8)]
            blob=b'MS'+bytes((len(records),0))+b''.join(struct.pack('>HB',i,v) for i,v in records)
            at=BASE-0x10000000+0x8ed80+part*0x18b2+0x17a2
            seed[at:at+144]=blob.ljust(144,b'\0')
            for i,v in records:scenes[part*4096+i]=v
        scenes=bytes(scenes)
    (w/'dense-cs1.bin').write_bytes(seed)
    for name,source,checkpoint in (('resume',w/'dense-cs1.bin',True),('again',w/'resume-cs1.bin',False)):
        extra=['--cs1-in',source,'--no-post','--sequencer','--internal-clock','--frames','1']
        if checkpoint:extra+=['--step','-:call:0x4000faf0,0']
        extra+=['--mem-dump',f'{sym["STORE"]:#x},98304={w}/{name}-p2.bin;{sym["ch_lock_table"]:#x},8192={w}/{name}-quality.bin;{sym["hd_banks"]:#x},16768={w}/{name}-roots.bin;{sym["scn_lib"]:#x},16384={w}/{name}-scenes.bin;0x10000000,0x100000={w}/{name}-cs1.bin']
        port.run(w,name,extra,image=image,card=w/'base-card.img')
        assert (w/f'{name}-p2.bin').read_bytes()==expected_p2,(name,'P2 mismatch')
        assert (w/f'{name}-quality.bin').read_bytes()==qualities,(name,'quality mismatch')
        roots=(w/f'{name}-roots.bin').read_bytes()
        actual_degrees=b''.join(roots[lane*131:lane*131+64] for lane in range(128))
        assert actual_degrees==degrees,(name,'degree mismatch')
        assert (w/f'{name}-scenes.bin').read_bytes()==scenes,(name,'Scenes mismatch')
        after=(w/f'{name}-cs1.bin').read_bytes()
        if not args.legacy:assert after[guard_start:guard_end]==seed[guard_start:guard_end],(name,'guard changed')
        assert after[0xf8600:0xf8604]==b'P2S1'
        assert after[0xf8620:0xf8624]==b'HDN3'
        assert after[0xfbdf0:0xfbdf4]==b'SCS1'
    # NEW PROJECT executes STORE's callbacks and the native OS body. A
    # retained restart of that result must never resurrect the dense state.
    for name,source,reset in (('new-project',w/'again-cs1.bin',True),
                              ('new-project-resume',w/'new-project-cs1.bin',False)):
        extra=['--cs1-in',source,'--no-post','--sequencer','--internal-clock','--frames','1']
        if reset:extra+=['--step',f'-:call:{sym["store_newproj"]:#x}']
        extra+=['--mem-dump',f'{sym["STORE"]:#x},1572864={w}/{name}-p2.bin;{sym["ch_lock_table"]:#x},131072={w}/{name}-quality.bin;{sym["scn_lib"]:#x},262144={w}/{name}-scenes.bin;0x10000000,0x100000={w}/{name}-cs1.bin']
        port.run(w,name,extra,image=image,card=w/'base-card.img')
        for store,length in (('p2',1572864),('quality',131072),('scenes',262144)):
            assert (w/f'{name}-{store}.bin').read_bytes()==b'\xff'*length,(name,store,'old state survived reset')
    result={'p2_locks':count,'p2_encoded_bytes':len(encoded),'harmony_step_tuples':8192,
            'midi_scenes_bytes':16384,'retained_restarts':2,'native_checkpoint':True,'native_new_project_and_retained_restart':True,
            'legacy_h8_migration':args.legacy,'capacities_reduced':False,'hardware_tested':False,
            'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest()}
    (port.OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
