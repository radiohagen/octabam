#!/usr/bin/env python3
"""Track-local Harmony with upstream PLOCKS retention through full firmware.

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
from verify_midi_sram import BASE, OFFSETS, symbols
from harmony_retained import raw_p2 as raw
from verify_harmony_track_retention import encode
from midi_machine import ROOT


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--project',required=True,type=Path)
    ap.add_argument('--candidate',type=Path,help='frozen directory with candidate.bin and candidate-all-symbols.json')
    args=ap.parse_args();port.OUT=ROOT/'out/harmony-track-port';port.OUT.mkdir(parents=True,exist_ok=True)
    w=port.fixture(args.project,'dense',{i:2 for i in range(8)},first_note=48)
    if args.candidate:
        image=args.candidate/'candidate.bin'
        sym=json.loads((args.candidate/'candidate-all-symbols.json').read_text())
    else:
        image=port.freeze_candidate(port.OUT);sym=symbols()
        (port.OUT/'candidate-all-symbols.json').write_text(json.dumps(sym,indent=2)+'\n')
    assert 'hd_track_read_c' in sym and 'plk_nv_encode' not in sym and 'plk_pool_encode' not in sym
    port.run(w,'base',['--sequencer','--internal-clock','--frames','1','--mem-dump',f'0x10000000,0x100000={w}/base-cs1.bin'],image=image)
    seed=bytearray((w/'base-cs1.bin').read_bytes())
    # Upstream PLOCKS retains 4,768 locks in its original 14,320 bytes.
    count=4768;records=[(i*19,i%128) for i in range(count)]
    expected_p2=bytearray(b'\xff'*98304)
    for i,v in records:expected_p2[i]=v
    encoded=raw(records,bank=0);assert len(encoded)==14320
    seed[0xf8600:0xfbdf0]=encoded
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
    checkpoint=encode(payload)
    for off,v in zip(OFFSETS,checkpoint):seed[BASE-0x10000000+off]=v
    # Fill all 4096 bytes in each of four Scene tables; no sparse shortcut.
    scenes=bytes((i*11+(i//4096)*17)%84 for i in range(16384))
    checksum=sum(struct.unpack('>4096I',scenes))&0xffffffff
    seed[0xfbdf0:0xfbe00]=struct.pack('>4I',0x53435331,0,checksum,0)
    seed[0xfbe00:0xffe00]=scenes
    (w/'dense-cs1.bin').write_bytes(seed)
    for name,source,checkpoint in (('resume',w/'dense-cs1.bin',True),('again',w/'resume-cs1.bin',False)):
        extra=['--cs1-in',source,'--no-post','--sequencer','--internal-clock','--frames','1']
        if checkpoint:extra+=['--step','-:call:0x4000faf0,0']
        extra+=['--mem-dump',f'{sym["STORE"]:#x},98304={w}/{name}-p2.bin;{sym["ch_lock_table"]:#x},8192={w}/{name}-quality.bin;{sym["hd_banks"]:#x},16768={w}/{name}-roots.bin;{sym["scn_lib"]:#x},16384={w}/{name}-scenes.bin;0x10000000,0x100000={w}/{name}-cs1.bin']
        port.run(w,name,extra,image=image,card=w/'base-card.img')
        assert 'DID NOT RETURN' not in (w/f'{name}.log').read_text(),name
        assert (w/f'{name}-p2.bin').read_bytes()==expected_p2,(name,'P2 mismatch')
        assert (w/f'{name}-quality.bin').read_bytes()==qualities,(name,'quality mismatch')
        roots=(w/f'{name}-roots.bin').read_bytes()
        actual_degrees=b''.join(roots[lane*131:lane*131+64] for lane in range(128))
        assert actual_degrees==degrees,(name,'degree mismatch')
        assert (w/f'{name}-scenes.bin').read_bytes()==scenes,(name,'Scenes mismatch')
        after=(w/f'{name}-cs1.bin').read_bytes()
        assert after[0xf8600:0xfbdf0]==encoded
        assert after[0x1aa6c] & 0xfc == 0xac
        assert after[0xfbdf0:0xfbdf4]==b'SCS1'
    # Clear a middle track using the complete native operation, then restart.
    lane=59
    for name,source,clear in (('clear-track',w/'again-cs1.bin',True),
                               ('clear-track-resume',w/'clear-track-cs1.bin',False)):
        extra=['--cs1-in',source,'--no-post','--sequencer','--internal-clock','--frames','1']
        if clear:extra+=['--step',f'-:call:0x40039b00,{lane//8},{lane%8},1',
                          '--step',f'-:call:{sym["hd_nv_poll_c"]:#x}']
        extra+=['--mem-dump',f'{sym["STORE"]:#x},98304={w}/{name}-p2.bin;{sym["ch_lock_table"]:#x},8192={w}/{name}-quality.bin;{sym["hd_banks"]:#x},16768={w}/{name}-roots.bin;{sym["scn_lib"]:#x},16384={w}/{name}-scenes.bin;0x10000000,0x100000={w}/{name}-cs1.bin']
        port.run(w,name,extra,image=image,card=w/'base-card.img')
        assert 'DID NOT RETURN' not in (w/f'{name}.log').read_text(),name
        expected_q=bytearray(qualities);expected_q[lane*64:(lane+1)*64]=b'\xff'*64
        expected_d=bytearray(degrees);expected_d[lane*64:(lane+1)*64]=b'\xff'*64
        assert (w/f'{name}-quality.bin').read_bytes()==expected_q,name
        roots=(w/f'{name}-roots.bin').read_bytes()
        assert b''.join(roots[i*131:i*131+64] for i in range(128))==expected_d,name
        assert (w/f'{name}-p2.bin').read_bytes()==expected_p2,name
        assert (w/f'{name}-scenes.bin').read_bytes()==scenes,name
    print('[ok] full native MIDI track clear survives restart; other tracks, PLOCKS and Scenes intact',flush=True)
    # NEW PROJECT executes STORE's callbacks and the native OS body. A
    # retained restart of that result must never resurrect the dense state.
    for name,source,reset in (('new-project',w/'again-cs1.bin',True),
                              ('new-project-resume',w/'new-project-cs1.bin',False)):
        extra=['--cs1-in',source,'--no-post','--sequencer','--internal-clock','--frames','1']
        if reset:extra+=['--step',f'-:call:{sym["store_newproj"]:#x}']
        extra+=['--mem-dump',f'{sym["STORE"]:#x},1572864={w}/{name}-p2.bin;{sym["ch_lock_table"]:#x},131072={w}/{name}-quality.bin;{sym["scn_lib"]:#x},262144={w}/{name}-scenes.bin;0x10000000,0x100000={w}/{name}-cs1.bin']
        port.run(w,name,extra,image=image,card=w/'base-card.img')
        assert 'DID NOT RETURN' not in (w/f'{name}.log').read_text(),name
        for store,length in (('p2',1572864),('quality',131072),('scenes',262144)):
            assert (w/f'{name}-{store}.bin').read_bytes()==b'\xff'*length,(name,store,'old state survived reset')
    result={'p2_locks':count,'p2_encoded_bytes':len(encoded),'harmony_step_tuples':8192,
            'midi_scenes_bytes':16384,'retained_restarts':2,'native_checkpoint':True,'native_new_project_and_retained_restart':True,
            'p2_matches_upstream_capacity':True,'harmony_capacity_reduced':False,'track_clear_restart':True,'hardware_tested':False,
            'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest()}
    (port.OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
