#!/usr/bin/env python3
"""Measure Loopback's real panel pixels on an immutable firmware candidate.

Adapted from Harmony's composed-LCD geometry checks (7825199b). Captures
both UART LCD output and composed RAM planes; edits use physical panel events.
No hardware is accessed. --candidate contains candidate.bin and symbols JSON.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
import midi_loopback_port as p
from panel.panel_server import PortProc
from panel.panel_link import PanelLink
import lcd_view


def ink(rows, left, right, top, bottom):
    points=[(x,y) for y in range(top,bottom+1) for x in range(left+1,right) if rows[y][x]]
    assert points, ('missing text/widget ink',left,right,top,bottom)
    bounds=[min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)]
    gaps=[bounds[0]-left-1,right-bounds[2]-1]
    assert min(gaps)>=1 and abs(gaps[0]-gaps[1])<=1, ('unbalanced or clipped ink',bounds,gaps)
    return dict(bounds=bounds,padding=gaps)


def measure(data, popup):
    rows=lcd_view.screen(data)
    if not popup:
        return dict(channel=ink(rows,59,79,23,27))
    windows=[]
    for i in range(5):
        at=1024+i*56
        flags,w,h=struct.unpack('>Iii',data[at+32:at+44])
        if flags&32 and (w,h)==(120,60):windows.append(struct.unpack('>ii',data[at+8:at+16]))
    assert len(windows)==1,('routing window missing/duplicated',windows)
    ox,oy=windows[0];left,right=ox+1,ox+117
    # Native frame ink starts at right, unlike the old short x=115 divider.
    for y in (oy+24,oy+47):
        gaps=[x for x in range(left,right+1) if not rows[y][x]]
        assert not gaps,('divider does not meet frame',y,gaps)
        assert not rows[y][left-1],('divider crosses the left frame',y,left-1)
    cells={name:ink(rows,left,ox+38,oy+1+a,oy+1+b)
           for name,a,b in [('label',2,6),('widget',7,13),('value',17,21)]}
    y0=min(v['bounds'][1] for v in cells.values());y1=max(v['bounds'][3] for v in cells.values())
    assert (y0-(oy+1)-1,(oy+24)-y1-1)==(1,1),('vertical padding',y0,y1)
    # The two content rows are equal; footer text stays inside the frame.
    assert (oy+24)-(oy+1)==(oy+47)-(oy+24)
    for x0,x1 in ((ox+2,ox+75),(ox+80,ox+116)):
        assert any(rows[y][x] for y in range(oy+50,oy+57) for x in range(x0,x1)), 'missing footer text'
    return dict(cells=cells,row_height=23,vertical_padding=[1,1],divider_right=right)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',type=Path,required=True)
    ap.add_argument('--candidate',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False);p.OUT=a.out
    sym=json.loads((a.candidate/'candidate-symbols.json').read_text())
    image=a.candidate/'candidate.bin';w=p.fixture(a.project,'panel')
    for f in (w/'project').glob('project.*'):
        s=re.sub(rb'MIDI_MODE=\d+',b'MIDI_MODE=0',f.read_bytes())
        s=re.sub(rb'(?m)^TRACK=\d+',b'TRACK=0',s);f.write_bytes(s)
    card,_=p.emu_card.stage_project(w/'project','OCTABAM','BASS',tree=w/'pixel-tree');(w/'card.img').write_bytes(card)
    keys=[0]*8;link=PanelLink();cases=[]
    proc=PortProc([p.ROOT/'out/emu/ot_emu','--image',image,'--card',w/'card.img','--mount',
        '--load-ms','90000','--set','OCTABAM','--project','BASS','--mkii',
        '--rtc','1800000000','--main-level','off','--interactive'])
    log=(w/'protocol.log').open('w')
    def cmd(s,e='ok'):
        r=proc.command(s,e);log.write(s+'\n'+r+'\n');log.flush();return r
    def peek(addr,n):
        return b''.join(bytes.fromhex(cmd(f'peek {addr+i:#x} {min(4096,n-i)}','peek').split()[1]) for i in range(0,n,4096))
    def key(code,edge=None):
        for down in ([True,False] if edge is None else [edge]):
            row,bit=code>>3,1<<(code&7);keys[row]=keys[row]|bit if down else keys[row]&~bit
            cmd(f'key {0x20+row} {keys[row]}');cmd('run '+('80' if down else '220'))
    def knob(n,d):cmd(f'knob {0x30+n} {d}');cmd('run 160')
    def settings(track):
        return peek(0x40170f60+0x4e2+36*track,36)
    def select_channel(track, target):
        # Native channel edits are staged until A is pressed. Observe the
        # committed value instead of assuming one report always means one step.
        for _ in range(34):
            old=settings(track)[0]
            if old!=target:knob(0,4 if target>old else -4)
            key(0x38)
            new=settings(track)[0]
            assert 0<=new<=16
            if new==target:return
            assert abs(new-target)<=abs(old-target),('channel moved away',old,new,target)
            key(0x32)
        raise AssertionError(('channel did not reach target',track,target))
    def select_route(track, target):
        # Stock 0x40032510 shares the encoder's fractional accumulator with
        # NOTE SETUP. A direction reversal can consume the first report.
        for _ in range(4):
            old=(settings(track)[12]>>2)&3
            if old==target:return
            residual=int.from_bytes(peek(0x46c7d244,4),'big',signed=True)
            knob(0,4 if target>old else -4)
            new=(settings(track)[12]>>2)&3
            assert abs(new-target)<=abs(old-target),('route moved away',old,new,target)
            log.write(f'route-progress {old} -> {new}; residual before {residual}\n');log.flush()
        assert (settings(track)[12]>>2)&3==target,('route did not reach target',track,target)
    def capture(name,popup,track,channel,route):
        link.feed(bytes.fromhex(cmd('tx','tx').partition(' ')[2]));rows=link.lcd_rows()
        (w/(name+'.png')).write_bytes(link.render_png(4))
        data=peek(0x46c7e0ea,1024)+peek(0x46c7d34c,280)+peek(0x460d1f7b,0x2800)
        (w/(name+'.lcd')).write_bytes(data)
        assert rows==lcd_view.screen(data),('UART/composed LCD mismatch',name)
        state=settings(track)
        assert state[0]==channel and (state[12]>>2)&3==route,(name,'wrong native settings',state.hex())
        assert bool(int.from_bytes(peek(sym['lb_page_win'],4),'big'))==popup
        layout=measure(data,popup)
        cases.append(dict(name=name,track=track+1,channel=channel,route=route,popup=popup,layout=layout,uart_ram_identical=True))
    try:
        proc.wait_ready(180);cmd('frame on');cmd('run 500');key(0x32)
        key(0x35);key(0x10);key(0x2d,True);key(0x22);key(0x2d,False)
        for track in range(8):
            key(0x10+track)
            for channel in ([0,1,16] if track==0 else [1]):
                select_channel(track,channel)
                for route in range(3):
                    select_route(track,route)
                    name=f'M{track+1}-CH{channel}-'+('EXT','INT','BOTH')[route]
                    capture(name+'-routing',True,track,channel,route)
                    key(0x32);capture(name+'-channel',False,track,channel,route)
                    if route<2:key(0x38)
            print(f'[ok] M{track+1} pixel geometry and channel indicators',flush=True)
        result=dict(status='PASS',image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
            test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=cases,
            hardware_tested=False,scope='Physical panel protocol in emulator; actual composed and UART pixels. No physical LCD or cold-start claim.')
        (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:proc.quit();log.close()


if __name__=='__main__':main()
