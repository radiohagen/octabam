#!/usr/bin/env python3
"""Native panel edit -> SAVE PROJECT -> virtual-card reload, no injected settings."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
import midi_loopback_port as p
from verify_midi_loopback_translation import machine
from verify_midi_loopback_ui_port import key
from panel.panel_server import PortProc


def save_interactive(w,image,script,sym):
    """Native SAVE driven by elapsed time, not audio-frame progress during I/O."""
    card=w/'save-card.img';shutil.copyfile(w/'card.img',card)
    proc=PortProc([p.ROOT/'out/emu/ot_emu','--image',image,'--card',card,'--card-rw',
        '--mount','--load-ms','90000','--set','OCTABAM','--project','BASS','--mkii',
        '--rtc','1800000000','--main-level','off','--interactive'])
    keys=[0]*8
    with (w/'save-protocol.log').open('w') as log:
        def cmd(s,expected='ok'):
            reply=proc.command(s,expected,timeout=55)
            log.write(s+'\n'+reply+'\n');log.flush();return reply
        def dump(address,length,name):
            data=b''.join(bytes.fromhex(cmd(f'peek {address+i:#x} {min(4096,length-i)}','peek').split()[1])
                for i in range(0,length,4096))
            (w/f'save-{name}.bin').write_bytes(data)
        try:
            proc.wait_ready(180);cmd('frame on');previous=0
            for line in script.splitlines():
                words=line.split();at=int(words[0]);remaining=at-previous
                while remaining:
                    step=min(500,remaining);reply=cmd(f'run {step} wall 15')
                    assert 'stop=time' in reply,reply
                    remaining-=step
                previous=at
                if words[1]=='quit':break
                if words[1]=='enc':cmd(f'knob {0x30+int(words[2])} {words[3]}')
                else:
                    assert words[1]=='key',words
                    code=int(words[2],0);row=code>>3;bit=1<<(code&7)
                    keys[row]=keys[row]|bit if words[3]=='down' else keys[row]&~bit
                    cmd(f'key {0x20+row} {keys[row]}')
            for address,length,name in ((sym['lt_work'],2560,'translation'),(0x100a4ece,25288,'parts'),
                (0x10000000,1048576,'cs1'),(0x46c7e0ea,1024,'plane'),
                (0x46c7d34c,280,'windows'),(0x460d1f7b,10240,'window-planes')):
                dump(address,length,name)
            assert 'errors=0' in cmd('card flush','card')
        finally:proc.quit()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',type=Path,required=True)
    ap.add_argument('--out',type=Path,default=p.ROOT/'out/midi-loopback-translation-port')
    ap.add_argument('--candidate',type=Path,help='Frozen image and matching symbol table')
    a=ap.parse_args()
    p.OUT=a.out
    if a.candidate:
        image=a.candidate/'candidate.bin'
        sym=json.loads((a.candidate/'candidate-symbols.json').read_text())
        p.CANDIDATE_IMAGE=image
        p.CANDIDATE_SYMBOLS=sym
    else:
        image=p.freeze_candidate(p.OUT)
        sym=machine().sym
        (p.OUT/'candidate-symbols.json').write_text(json.dumps(sym,indent=2)+'\n')
    w=p.fixture(a.project,'panel',{})
    for file in (w/'project').glob('project.*'):
        raw=re.sub(rb'MIDI_MODE=\d+',b'MIDI_MODE=0',file.read_bytes())
        file.write_bytes(re.sub(rb'(?m)^TRACK=\d+',b'TRACK=0',raw))
    card,_=p.emu_card.stage_project(w/'project','OCTABAM','BASS',tree=w/'ui-tree')
    (w/'card.img').write_bytes(card)
    base=key(100,0x31)+key(600,0x35)+key(1100,0x10)
    base+='1600 key 0x2d down\n1700 key 0x22 down\n1850 key 0x22 up\n1950 key 0x2d up\n'
    # Commit native channel and open the established routing window.
    opened=base+'2300 enc 0 4\n'+key(2500,0x38)
    # A BOTH and B EXT: independent route/apply selectors, other fields preset.
    edit=opened+'2800 enc 0 4\n2900 enc 0 4\n3100 enc 1 4\n3200 enc 1 4\n'
    def run(name,script,card=None,extra=()):
        print('[run]',name,flush=True)
        panel=w/(name+'.txt');panel.write_text(script)
        # Final-state pixels suffice here; avoid unnecessary live LCD watches
        # during the full-project save. Interactive pixel coverage is separate.
        p.run(w,name,['--rtc','1800000000','--live-script',panel,
            '--mem-dump',f'{sym["lt_work"]:#x},2560={w}/{name}-translation.bin;'
            f'0x100a4ece,25288={w}/{name}-parts.bin;0x10000000,1048576={w}/{name}-cs1.bin;'
            f'0x46c7e0ea,1024={w}/{name}-plane.bin;0x46c7d34c,280={w}/{name}-windows.bin;'
            f'0x460d1f7b,10240={w}/{name}-window-planes.bin',
            *extra],card=card,physical_panel=True)
        (w/(name+'.lcd')).write_bytes(b''.join((w/f'{name}-{part}.bin').read_bytes()
            for part in ('plane','windows','window-planes')))
        return (w/(name+'-translation.bin')).read_bytes()
    initial=run('off',opened+'2900 quit\n')
    assert initial==bytes(2560)
    state=run('edit',edit+'3500 quit\n')
    assert state[:5]==bytes((2,60,84,12,1)) and not any(state[5:]),state[:40].hex()
    parts=(w/'edit-parts.bin').read_bytes()
    assert parts[0x4e2+12]==8 and parts[0x4e2]==2
    subprocess.run([str(p.ROOT/'.venv/bin/python'),str(p.ROOT/'tools/emu/lcd_view.py'),
        str(w/'edit.lcd'),'--png',str(w/'edit.png')],check=True,stdout=subprocess.DEVNULL)
    close=edit+key(4500,0x38)+key(4900,0x32)
    for at,k in zip(range(5500,9700,700),[0x1c,0x21,0x20,0x31,0x31]): close+=key(at,k)
    print('[run] save (interactive native clock)',flush=True)
    save_script=close+'40000 quit\n';(w/'save.txt').write_text(save_script)
    save_interactive(w,image,save_script,sym)
    assert (w/'save-translation.bin').read_bytes()==state
    files=p.emu_card.extract_image((w/'save-card.img').read_bytes())
    for bank in range(1,17):
        base=f'OCTABAM/BASS/bank{bank:02d}'
        assert files[base+'.strd']==files[base+'.work'],('native save incomplete',bank)
    for name in ('lbnt01.work','lbnt01.strd'):
        data=files['OCTABAM/BASS/'+name]
        assert len(data)==336 and data[:4]==b'LBNT'
        assert data[16:176]==state[:160],(name,data.hex())
    for name,extra in [('reload',()),('warm',('--no-post','--cs1-in',w/'save-cs1.bin'))]:
        assert run(name,'1500 quit\n',w/'save-card.img',extra)==state,name
    assert run('fresh','1500 quit\n',extra=('--cs1-in',w/'save-cs1.bin'))==bytes(2560)
    # A physical turn of each mapping encoder edits only its own field.
    changed=run('fields',edit+'3500 enc 2 4\n3600 enc 3 4\n3700 enc 4 4\n3800 enc 5 4\n4200 quit\n')
    assert changed[:5]==bytes((2,61,85,13,1)),changed[:5].hex()
    result={'status':'pass','image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
        'checks':['OFF default','independent physical DEST/RE-MAP','manual reference/range encoders',
                  'native SAVE PROJECT companion work and stored','disk reload','retained resume','fresh project OFF'],
        'scope':'full firmware under emulator, virtual card, no hardware acceptance'}
    (p.OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('[ok] physical panel mapping, native SAVE PROJECT, virtual-card reload/resume and fresh-project OFF')


if __name__=='__main__': main()
