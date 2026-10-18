#!/usr/bin/env python3
"""Translation UX: real panel events, UART/composed pixels and six-cell geometry."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
import midi_loopback_port as p
from panel.panel_server import PortProc
from panel.panel_link import PanelLink
from verify_midi_loopback_pixels import ink
import lcd_view


def measure(data):
    rows=lcd_view.screen(data);windows=[]
    for i in range(5):
        at=1024+i*56
        flags,w,h=struct.unpack('>Iii',data[at+32:at+44])
        if flags&32 and (w,h)==(120,60):windows.append(struct.unpack('>ii',data[at+8:at+16]))
    assert len(windows)==1,windows
    ox,oy=windows[0]
    for y in (oy+30,):
        assert all(rows[y][x] for x in range(ox+1,ox+118)),'broken divider'
    result={}
    for i,(left,right) in enumerate(((1,38),(38,77),(77,117))):
        for row in range(2):
            top=oy+row*29
            if row==1 and i==2:
                assert not any(rows[y][x] for y in range(top+2,top+28)
                               for x in range(ox+left+1,ox+right)), 'unused F is not blank'
                continue
            selector=row==0 and i<2
            numeric=row==1
            result['ABCDEF'[i+3*row]]={
                'label':ink(rows,ox+left,ox+right,top+3,top+7),
                'value':ink(rows,ox+left,ox+right,
                            top+(21 if numeric else 18 if selector else 12),
                            top+(25 if numeric else 22 if selector else 16))}
            if selector:
                result['ABCDEF'[i+3*row]]['widget']=ink(rows,ox+left,ox+right,top+8,top+14)
            elif numeric:
                result['ABCDEF'[i+3*row]]['widget']=ink(rows,ox+left,ox+right,top+9,top+19)
                for y in (top+8,top+20,top+26):
                    assert not any(rows[y][x] for x in range(ox+left+1,ox+right)), 'stock dial overlaps label/value'
            else:
                # NOTE-style text, no dial/label overlap or stale selector icon.
                assert not any(rows[y][x] for y in range(top+8,top+12)
                               for x in range(ox+left+1,ox+right))
                assert not any(rows[y][x] for y in range(top+17,top+23)
                               for x in range(ox+left+1,ox+right))
    return result


def inactive_pixels(off,on):
    """OFF keeps ordinary stock values/graphics: only RE-MAP changes visually."""
    before,after=lcd_view.screen(on),lcd_view.screen(off)
    windows=[]
    for i in range(5):
        at=1024+i*56
        flags,w,h=struct.unpack('>Iii',on[at+32:at+44])
        if flags&32 and (w,h)==(120,60):windows.append(struct.unpack('>ii',on[at+8:at+16]))
    ox,oy=windows[0]
    for y in range(1,59):
        for x in range(1,118):
            if 38<x<77 and y<30:continue # RE-MAP selector itself changes.
            assert after[oy+y][ox+x]==before[oy+y][ox+x],('OFF changed stock control pixels',x,y)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',type=Path,required=True)
    ap.add_argument('--candidate',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False);p.OUT=a.out
    if a.candidate:
        sym=json.loads((a.candidate/'candidate-symbols.json').read_text())
        image=a.candidate/'candidate.bin'
    else:
        from verify_midi_loopback_translation import machine
        image=p.freeze_candidate(a.out/'candidate');sym=machine().sym
        (a.out/'candidate/candidate-symbols.json').write_text(json.dumps(sym,indent=2)+'\n')
    w=p.fixture(a.project,'panel')
    for file in (w/'project').glob('project.*'):
        raw=re.sub(rb'MIDI_MODE=\d+',b'MIDI_MODE=0',file.read_bytes())
        file.write_bytes(re.sub(rb'(?m)^TRACK=\d+',b'TRACK=0',raw))
    card,_=p.emu_card.stage_project(w/'project','OCTABAM','BASS',tree=w/'pixel-tree')
    (w/'card.img').write_bytes(card)
    keys=[0]*8;link=PanelLink();cases=[];captures={}
    proc=PortProc([p.ROOT/'out/emu/ot_emu','--image',image,'--card',w/'card.img','--mount',
        '--load-ms','90000','--set','OCTABAM','--project','BASS','--mkii',
        '--rtc','1800000000','--main-level','off','--interactive'])
    log=(w/'protocol.log').open('w')
    def cmd(s,e='ok'):
        r=proc.command(s,e);log.write(s+'\n'+r+'\n');log.flush();return r
    def peek(at,n):
        return bytes.fromhex(cmd(f'peek {at:#x} {n}','peek').split()[1])
    def key(code,edge=None):
        for down in ([True,False] if edge is None else [edge]):
            row,bit=code>>3,1<<(code&7);keys[row]=keys[row]|bit if down else keys[row]&~bit
            cmd(f'key {0x20+row} {keys[row]}');cmd('run '+('80' if down else '220'))
    def knob(n,d):cmd(f'knob {0x30+n} {d}');cmd('run 160')
    def values(track=0):
        record=peek(sym['lt_work']+track*5,5)
        return list(record[:4]) if record[4] else [0,60,84,12]
    def set_field(field,target):
        for _ in range(260):
            before=values()[field]
            if before==target:return
            knob(field+1,4 if before<target else -4)
            after=values()[field]
            assert abs(after-target)<=abs(before-target),(field,before,after,target)
        raise AssertionError(('encoder did not reach value',field,target,values()))
    def capture(name,track=0):
        link.feed(bytes.fromhex(cmd('tx','tx').partition(' ')[2]))
        data=peek(0x46c7e0ea,1024)+peek(0x46c7d34c,280)
        data+=b''.join(peek(0x460d1f7b+i,min(4096,0x2800-i)) for i in range(0,0x2800,4096))
        assert link.lcd_rows()==lcd_view.screen(data),(name,'UART/composed mismatch')
        (w/(name+'.png')).write_bytes(link.render_png(4));(w/(name+'.lcd')).write_bytes(data)
        captures[name]=data
        layout=measure(data)
        cases.append(dict(name=name,track=track+1,values=values(track),layout=layout,uart_ram_identical=True))
    try:
        proc.wait_ready(180);cmd('frame on');cmd('run 500');key(0x32)
        key(0x35);key(0x10);key(0x2d,True);key(0x22);key(0x2d,False);key(0x38)
        capture('default-off')
        for encoder in range(2,6):knob(encoder,4)
        assert values()==[0,60,84,12],'OFF mapping controls changed stored values'
        capture('off-controls-inactive')
        for route in range(3):
            for _ in range(4):
                current=(peek(0x40171442+12,1)[0]>>2)&3
                if current==route:break
                knob(0,4 if current<route else -4)
            assert (peek(0x40171442+12,1)[0]>>2)&3==route
            for mode in range(4):
                set_field(0,mode);capture(f'dest-{route}-apply-{mode}')
            inactive_pixels(captures[f'dest-{route}-apply-0'],captures[f'dest-{route}-apply-1'])
        set_field(3,63)
        knob(4,4)
        assert values()[3]==63,'RANGE exceeded ±63'
        for source in (0,1,60,127):
            set_field(1,source);capture(f'source-{source}')
        for target in (0,9,10,99,100,127):
            set_field(2,target);capture(f'target-{target}')
        for radius in (0,1,12,62,63):
            set_field(3,radius);capture(f'range-{radius}')
            if radius==0:
                knob(4,-4)
                assert values()[3]==0,'RANGE went below ±0'
        before=values();knob(5,4)
        assert values()==before,'unused F changed a mapping field'
        set_field(0,0);capture('edited-inactive')
        before=values()
        for encoder in range(2,6):knob(encoder,4)
        assert values()==before,'OFF edited mapping changed'
        set_field(0,3);capture('edited-active')
        inactive_pixels(captures['edited-inactive'],captures['edited-active'])
        # Close semantics and track changes, using actual native events.
        for code in (0x38,0x31,0x32,0x23):
            before=values();key(code)
            assert peek(sym['lb_page_win'],4)==bytes(4) and values()==before
            if code==0x23:
                key(0x2d,True);key(0x22);key(0x2d,False)
            key(0x38)
        for track in range(1,8):
            key(0x10+track);assert peek(sym['lb_page_win'],4)==bytes(4)
            key(0x38);assert values(track)==[0,60,84,12]
            capture(f'M{track+1}-default',track)
        result=dict(status='PASS',image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
            cases=cases,hardware_tested=False,
            scope='Physical panel events, all six cells, actual UART/composed pixels; emulator only.')
        (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(f'[ok] {len(cases)} translation screens: centered labels/values, bounds, all tracks, UART/composed identity and close behavior')
    finally:proc.quit();log.close()


if __name__=='__main__':main()
