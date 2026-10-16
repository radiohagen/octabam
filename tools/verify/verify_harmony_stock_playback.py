#!/usr/bin/env python3
"""Measure native NOTE mirrors on stock after a Harmony project save.

Uses a copied project, native transport and SAVE PROJECT, then cold boots
stock and the candidate from the saved virtual card. No device is accessed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import verify_midi_harmony_port as p
from verify_chord_play_port import SAVE


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',required=True,type=Path)
    args=ap.parse_args()
    p.OUT=p.ROOT/'out/harmony-stock-playback'
    candidate=p.freeze_candidate(p.OUT)
    symbols=p.harmony.symbols()
    (p.OUT/'receipt.json').unlink(missing_ok=True)
    # Author the extension through its native UI. Seeding HARM active without
    # its companion would test missing-file recovery instead of a saved project.
    w=p.fixture(args.project,'d-minor',{},key_raw=6,first_note=50)
    # One root per event, with no native extra chord tones to confound the
    # degree-mirror comparison. Other tracks have no external channel.
    for bank in (w/'project').glob('bank*.work'):
        def seed(data):
            for part in range(8):
                base=p.otp.PART_BASE+part*p.otp.PART_STRIDE+9
                for track in range(1,8):data[base+0x4e2+36*track]=0
            for pattern in range(16):
                at=0x492e+pattern*0x8eec+0x39
                for step in range(64):data[at+step*32+3:at+step*32+6]=b'\xff'*3
        p.otp._bank_write(w/'project',int(bank.stem[4:]),seed,guard=False)
    card,_=p.emu_card.stage_project(w/'project','OCTABAM','BASS',tree=w/'seed-tree')
    (w/'seed.img').write_bytes(card)
    transport='1900 key 0x28 down\n1980 key 0x28 up\n5200 key 0x27 down\n5280 key 0x27 up\n'
    dismiss='100 key 0x32 down\n180 key 0x32 up\n'
    enable=('300 key 0x35 down\n350 key 0x35 up\n500 key 0x2d down\n'
            '600 key 0x22 down\n650 key 0x22 up\n700 key 0x2d up\n'
            '1000 enc 5 4\n1200 key 0x32 down\n1280 key 0x32 up\n')
    rows=[];companions=None
    for label,image,source,wanted in [
        ('candidate',candidate,w/'seed.img',[50,65,67]),
        ('candidate-cold',candidate,w/'candidate-card.img',[50,65,67]),
        ('stock',p.ROOT/'out/raw/section_3_MAIN_OS.bin',w/'candidate-cold-card.img',[48,64,65]),
        ('return',candidate,w/'stock-card.img',[50,65,67]),
    ]:
        script=w/f'{label}-play-save.txt'
        script.write_text(dismiss+(enable if label=='candidate' else '')+transport+SAVE)
        extra=[]
        if label!='stock':
            extra=['--mem-dump',f'{symbols["ch_lock_status"]:#x},16={w}/{label}-status.bin']
        events=p.run(w,label,['--rtc','1800000000','--internal-clock','--live-script',script,*extra],image=image,card=source)
        p.balanced(events)
        notes=[e[2] for e in events if e[:2]==('on',1)]
        assert notes==wanted,(label,notes,wanted)
        if label!='stock':
            assert (w/f'{label}-status.bin').read_bytes()[0]==1, (label,'companion must validate and save successfully')
        files=p.emu_card.extract_image((w/f'{label}-card.img').read_bytes())
        current={k:hashlib.sha256(v).hexdigest() for k,v in files.items() if '/hdeg' in k.lower()}
        assert current,(label,'no saved Harmony companion')
        if label=='candidate':companions=current
        if label=='stock':assert current==companions,'stock changed Harmony companions'
        rows.append(dict(stage=label,notes=notes,image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),companion_hashes=current))
        print('[ok]',label,'native transport/save MIDI roots',notes,flush=True)
    (p.OUT/'receipt.json').write_text(json.dumps(dict(status='pass',runs=rows,hardware_tested=False,
        scope='HARM NOTE, D minor, three explicit roots, no stock edits. Does not prove arbitrary stock edits or retained-memory firmware switching safe.'),indent=2)+'\n')

if __name__=='__main__':main()
