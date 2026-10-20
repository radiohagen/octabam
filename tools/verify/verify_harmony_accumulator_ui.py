#!/usr/bin/env python3
"""Measure actual composed 1-bpp LCD ink, not nominal widget coordinates."""
import json
import struct
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/emu'))
import lcd_view


def measure_accum(rows, ox, oy, name, chord_rows):
    """Reject any ink outside the title, native graphic and value bands."""
    edges=[ox+i for i in (32,60,88,117)]
    tops=[oy+i for i in (1,29,57)]
    cells=[]
    for cell in range(6):
        col,row=cell%3,cell//3
        left,right=edges[col:col+2]
        top,bottom=tops[row:row+2]
        points={(x,y) for y in range(top+1,bottom)
                for x in range(left+1,right) if rows[y][x]}
        if cell>=4:
            assert not points,(name,cell,'unused encoder cell contains ink')
            continue
        # Actual 1-bpp native bounds: dial 11x11, switch 17x7, text 5px tall.
        bands=(('title',2,6),('graphic',8,18),('value',20,24)) if cell<2 else (
            ('title',2,6),('graphic',9,15),('value',19,23))
        covered=set()
        for kind,first,last in bands:
            ink={(x,y) for x,y in points if top+first<=y<=top+last}
            assert ink,(name,cell,kind,'missing')
            x0=min(x for x,y in ink); x1=max(x for x,y in ink)
            y0=min(y for x,y in ink); y1=max(y for x,y in ink)
            assert (y0,y1)==(top+first,top+last),(name,cell,kind,'clipped height',y0,y1)
            gaps=(x0-left-1,right-x1-1)
            assert min(gaps)>=1 and abs(gaps[0]-gaps[1])<=1,(name,cell,kind,'off centre',gaps)
            if kind=='graphic':
                width=11 if cell<2 else 17
                assert x1-x0+1==width,(name,cell,'clipped graphic',x0,x1)
                if cell>=2:
                    assert all(rows[y][x] for y in (y0,y1)
                               for x in range(x0,x1+1)),(name,cell,'incomplete switch border')
            covered |= ink
            cells.append(dict(cell=cell,kind=kind,bounds=[x0,y0,x1,y1],
                              left_right_padding=list(gaps)))
        assert points==covered,(name,cell,'ink in title/widget/value gap',sorted(points-covered))
    # Preserve native CHORD/ACCUM menu pixels, changing only its XOR selection.
    for y in range(oy+2,oy+27):
        for x in range(ox+3,ox+31):
            inverted=(oy+4<=y<=oy+11 or oy+15<=y<=oy+22)
            assert rows[y][x]==(chord_rows[y][x]^inverted),(name,'menu changed',x,y)
    assert all(rows[y][edges[0]] for y in range(oy+1,oy+58)),(name,'missing menu divider')
    for x in edges[1:3]:
        for start,end in ((oy+2,oy+28),(oy+30,oy+56)):
            column=[rows[y][x] for y in range(start,end)]
            assert all(a!=b for a,b in zip(column,column[1:])),(name,'missing dotted column',x)
    divider=rows[tops[1]][edges[0]+1:edges[-1]]
    assert all(a!=b for a,b in zip(divider,divider[1:])),(name,'missing dotted row')
    return dict(cells=cells,grid=[32,60,88,117],footer='omitted',
                menu='native CHORD/ACCUM with ACCUM selected',
                max_horizontal_centre_error_pixels=0.5)


def measure(directory):
    results={}
    chord_rows=lcd_view.screen(lcd_view.read_plane(directory/'harmony-page.lcd'))
    captures=[('harmony-page',False,0),('chord-page-extremes',False,0),('accum-page',False,1)]
    captures += [(p.stem,False,1) for p in sorted(directory.glob('accum-state-*.lcd'))]
    for name,plain,selected in captures:
        data=lcd_view.read_plane(directory/f'{name}.lcd')
        rows=lcd_view.screen(data)
        windows=[]
        for i in range(5):
            at=lcd_view.WIN_TABLE+i*56
            flags,w,h=struct.unpack('>Iii',data[at+32:at+44])
            if flags&32 and (w,h)==(120,60):
                windows.append(struct.unpack('>ii',data[at+8:at+16]))
        assert len(windows)==1,(name,windows)
        ox,oy=windows[0]
        # Native frame's inner right edge is x=117, not the old short
        # horizontal line endpoint x=115. This distinction caught real drift.
        if name.startswith('accum-'):
            results[name]=measure_accum(rows,ox,oy,name,chord_rows)
            if name=='accum-page':
                # Prove this gate detects the defects it guards, using a
                # single corrupt pixel in each independently checked region.
                for defect,x,y in (('overlap',46,8),('unused E',74,38),
                                   ('clipped switch',95,10),('lost menu',5,15)):
                    bad=[row[:] for row in rows]
                    bad[oy+y][ox+x]^=1
                    try:
                        measure_accum(bad,ox,oy,defect,chord_rows)
                    except AssertionError:
                        pass
                    else:
                        raise AssertionError(('pixel gate missed defect',defect))
                results[name]['negative_controls']='overlap, E/F ink, clipped switch, lost menu rejected'
            continue
        edges=[ox+i for i in (32,60,88,117)]
        tops=[oy+1,oy+24,oy+47]
        for x in edges[1:3]:
            # The native dotted verticals deliberately leave their last two
            # pixels open where they meet the horizontal divider.
            column=[rows[y][x] for y in range(tops[0]+1,tops[1])]
            assert all(a!=b for a,b in zip(column,column[1:])),(name,'not dotted',x)
        values=[]
        for cell in range(4):
            col,row=cell%3,cell//3
            left,right=edges[col:col+2];top,bottom=tops[row:row+2]
            bands=(('label',5,9),('value',14,18)) if plain else (
                ('label',2,6),('graphic',7,13),('value',17,21))
            all_points=[]
            for kind,first,last in bands:
                points=[(x,y) for y in range(top+first,top+last+1)
                        for x in range(left+1,right) if rows[y][x]]
                assert points,(name,cell,kind,'missing ink')
                all_points+=points
                x0=min(x for x,y in points);x1=max(x for x,y in points)
                gaps=(x0-left-1,right-x1-1)
                assert min(gaps)>=1 and abs(gaps[0]-gaps[1])<=1,(name,cell,kind,gaps)
                values.append(dict(cell=cell,kind=kind,bounds=[x0,min(y for x,y in points),
                    x1,max(y for x,y in points)],left_right_padding=list(gaps)))
            y0=min(y for x,y in all_points);y1=max(y for x,y in all_points)
            gaps=(y0-top-1,bottom-y1-1)
            assert gaps==((4,4) if plain else (1,1)),(name,cell,'vertical padding',gaps)
        # The selection bar must contain dark glyph ink, not a blank fill.
        top=oy+(6 if selected==0 else 17)
        ink=[rows[y][x] for y in range(top,top+5) for x in range(ox+5,ox+24)]
        assert 0 in ink and 1 in ink,(name,'blank selection label')
        results[name]=dict(cells=values,vertical_padding=[4,4] if plain else [1,1],
                           max_horizontal_centre_error_pixels=0.5)
    states=sorted(directory.glob('accum-state-*.lcd'))
    if states:
        assert len(states)==4,'capture all four switch positions'
        for cell in (2,3):
            signatures=[]
            for path in states:
                rows=lcd_view.screen(lcd_view.read_plane(path))
                band=next(b for b in results[path.stem]['cells']
                          if b['cell']==cell and b['kind']=='graphic')
                x0,y0,x1,y1=band['bounds']
                signatures.append(tuple(tuple(rows[y][x0:x1+1]) for y in range(y0,y1+1)))
            assert len(set(signatures))==4,('switch graphic does not follow all four values',cell)
    (directory/'pixel-layout.json').write_text(json.dumps(results,indent=2)+'\n')
    print('[ok] LCD pixels: all labels/graphics/values within 0.5 px of cell centre; separate ACCUM title/graphic/value bands, native menu and empty E/F',flush=True)
    return results


if __name__=='__main__':
    measure(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'out/harmony-accumulator-port/panel-note')
