#!/usr/bin/env python3
"""RETURNS' real DSP instructions against a bit-exact integer mix model.

Uses the image's stock frame setup, with the module assembled separately so
wrong-track/core calls can be exercised deliberately. The full firmware
post-fader gate covers the installed hook, engine routing and live mute tails.
No hardware timing claim is made by this arithmetic/ownership gate.
"""
import importlib.util
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import toolpath  # noqa: E402,F401
from remix import registry
import send_probe

OUT = ROOT / 'out/verify_returns'
Q = 1 << 23
MAGIC = 0x5a5a5a
STRIDE = 512


def sat(v):
    return max(-Q, min(Q-1, v))


def signed(v):
    return (v & 0x7fffff) - (v & 0x800000)


def gain(knob, previous):
    v = knob & 0x7f0000
    return (v*v + 3*(previous & 0x7fffff)*Q) // (4*Q)


def model(row):
    """All persisted observables, including words the hook must leave alone."""
    out = [0] * STRIDE
    out[:5] = [0x1234, 0x9800, row[1], 16, 0xffffff]
    out[5:13] = row[5:13]
    out[16:472] = row[16:472]
    action, _, payload = row[:3]
    if action in (1, 2):
        if payload == 0 and row[1] == 0x6b00:
            if action == 1:
                out[8] = out[11] = 0
            else:
                out[5], out[6], out[10], out[12] = MAGIC, row[15], row[14], MAGIC
        return out
    for call in range(2 if action == 3 else 1):
        out[8] = rg = gain(out[6], out[8])
        out[11] = dg = gain(out[10], out[11])
        offset = (row[4]+0x50) & 0x70
        stamp = 304 + (offset >> 4)
        if out[stamp] != 0x5a0000+offset:
            dg = 0
        out[stamp] = 0
        fresh = out[7] == MAGIC
        if not fresh:
            rg = 0
            if dg == 0:
                continue
        out[7] = 0
        if not row[3]:
            rg, dg = rg*0x47e9ff//Q, dg*0x47e9ff//Q
        for i in range(32):
            rv, dl = signed(row[16+i]), signed(row[48+2*offset+i])
            at = 440+i if row[3] else 312+(i//2)*8+2+(i%2)
            scale = 1 if row[3] else 4
            out[at] = sat((signed(out[at])*Q + (rv*rg+dl*dg)*scale)//Q) & 0xffffff
    return out


def fixtures():
    rng = random.Random(542)
    rows, names = [], []
    def add(name, *, action=0, track=0x6b00, payload=0, master=0,
            rotation=0, fresh=True, stamped=True, knob=108, old=None):
        row = [0]*STRIDE
        row[:5] = [action, track, payload, master, rotation]
        row[5:13] = [0x13579b, (knob<<16)|0xffff,
                     MAGIC if fresh else 0xace, 0x321234 if old is None else old,
                     0x456789, ((127-knob)<<16)|0xabcd,
                     0x123456 if old is None else old, 0x876543]
        row[14:16] = [0x5c1234, 0x376789]
        for at in range(16,304):
            row[at] = rng.randrange(-Q, Q) & 0xffffff
        # Distinct protected words expose a one-word output/pointer slip.
        row[304:312] = [0xabcdef]*8
        off=(rotation+0x50)&0x70
        row[304+(off>>4)] = 0x5a0000+off if stamped else 0x5a0000+(off^0x10)
        for at in range(312,472):
            row[at] = rng.randrange(-Q,Q)&0xffffff
        rows.append(row); names.append(name)
    for knob in range(128):
        add(f'gain-{knob}', knob=knob, old=(0,0x7fffff,0xabcdef)[knob%3],
            master=knob%2, rotation=(knob%8)*16)
    for master in (0,1):
        for rotation in range(0,128,16):
            for fresh, stamped in ((False,False),(False,True),(True,False),(True,True)):
                add(f'mix-{master}-{rotation}-{fresh}-{stamped}', master=master,
                    rotation=rotation, fresh=fresh, stamped=stamped)
    for payload in (0,1):
        for track in (0x6200,0x6500,0x6800,0x6b00):
            for action in (1,2):
                add(f'guard-{payload}-{track:x}-{action}', action=action,
                    payload=payload, track=track)
    for master in (0,1):
        add(f'consume-once-{master}', action=3,master=master)
        add(f'zero-gain-stale-{master}', master=master,knob=127,old=0,fresh=False)
    assert len(rows)*STRIDE <= 0x20000
    return rows, names


def record(space, address, values):
    return struct.pack('<BII',space,address,len(values)) + struct.pack('<'+'I'*len(values), *values)


def wrapper(a, b):
    # Only the wrapper seeds/copies memory. Calls go into the unmodified module.
    return f'''
boot:
        clr a
        move a,y:>$f00
        rts
step:
        move r7,y:>$f03
        move r6,y:>$f04
        move r0,y:>$f05
        move #>$ffffff,m0
        move #>$ffffff,m1
        move #>$ffffff,m2
        move #>$ffffff,m3
        move #>$ffffff,m4
        move y:>$f00,a
        asl #$9,a,a
        add #>$10000,a
        move a,r2
        move a,y:>$f01
        move a,y:>$f02
        lua (r2+$5),r2
        move #>$e20,r3
        move #>$7,n2
        bsr copyy
        move x:(r2)+,a
        move a,y:>$30208
        lua (r2+$3),r2
        move #>$e00,r3
        move #>$20,n2
        bsr copyy
        move #>$30100,r3
        move #>$100,n2
        bsr copyx
        move #>$30200,r3
        move #>$8,n2
        bsr copyy
        move #>$9000,r3
        move #>$80,n2
        bsr copyx
        move #>$9200,r3
        move #>$20,n2
        bsr copyx
        move y:>$f01,r2
        move x:(r2+$3),a
        asl #$a,a,a
        move a,x:>$947e
        move x:(r2+$4),a
        move a,y:>$36000
        move x:(r2+$e),a
        move a,x:>$9800
        move x:(r2+$f),a
        move a,x:>$9801
        move #>$9400,r1
        move r1,x:>$207
        move #>$9000,r1
        move r1,x:>$203
        move #>$9008,r1
        move r1,x:>$209
        move #>$1234,r0
        move r0,x:>$206
        move #>$9800,r6
        move x:(r2+$1),r7
        move x:(r2),a
        cmp #>$1,a
        beq oncei
        cmp #>$2,a
        beq oncep
        move #>${a['mixhook']:x},r5
        jsr (r5)
        move x:(r2),a
        cmp #>$3,a
        bne snap
        move #>${a['mixhook']:x},r5
        jsr (r5)
        bra snap
oncei:
        move x:(r2+$2),a
        tst a
        bne corei
        move #>${a['init']:x},r5
        jsr (r5)
        bra snap
corei:
        move #>${b['init']:x},r5
        jsr (r5)
        bra snap
oncep:
        move x:(r2+$2),a
        tst a
        bne corep
        move #>${a['proc']:x},r5
        jsr (r5)
        bra snap
corep:
        move #>${b['proc']:x},r5
        jsr (r5)
snap:
        move y:>$f02,r3
        move r0,y:(r3)+
        move r6,y:(r3)+
        move r7,y:(r3)+
        move n7,y:(r3)+
        move m0,y:(r3)+
        move #>$e20,r2
        move #>$7,n2
        bsr fromy
        move y:>$30208,a
        move a,y:(r3)+
        lua (r3+$3),r3
        move #>$e00,r2
        move #>$20,n2
        bsr fromy
        move #>$30100,r2
        move #>$100,n2
        bsr copyy
        move #>$30200,r2
        move #>$8,n2
        bsr fromy
        move #>$9000,r2
        move #>$80,n2
        bsr copyy
        move #>$9200,r2
        move #>$20,n2
        bsr copyy
        move y:>$f00,a
        add #>$1,a
        move a,y:>$f00
        move y:>$f03,r7
        move y:>$f04,r6
        move y:>$f05,r0
        rts
copyx:
        do n2,>cxend
        move x:(r2)+,a
        move a,x:(r3)+
cxend:
        rts
copyy:
        do n2,>cyend
        move x:(r2)+,a
        move a,y:(r3)+
cyend:
        rts
fromy:
        do n2,>fyend
        move y:(r2)+,a
        move a,y:(r3)+
fyend:
        rts
'''


def installed(remix, image, source, assemble):
    """The arithmetic gate must exercise exactly the bytes placed in the image."""
    module = registry.bound(registry.remix(remix))['RETURNS']
    for tag in 'AB':
        path = send_probe.dump_mem(image, OUT/f'installed_{tag}.mem', tag)
        blob = path.read_bytes()
        init, proc = send_probe.entry_points(path, module.menu.fx2_id)
        guard = '; payload A' if tag == 'A' else 'rts'
        words, syms = assemble(source.replace('@RETURNS_CORE_GUARD@',guard), init,
                              f'installed RETURNS {tag}')
        program, pos = {}, 0
        while pos+9 <= len(blob):
            space, address, count = struct.unpack_from('<BII',blob,pos); pos += 9
            if space == 255: break
            if space == 0:
                values = struct.unpack_from('<'+'I'*count,blob,pos)
                program.update((address+i,v) for i,v in enumerate(values))
            pos += 4*count
        assert proc == syms['proc'], (tag, 'dispatch')
        assert [program.get(init+i) for i in range(len(words))] == words, (tag, 'module bytes')
        if tag == 'A':
            assert [program.get(0x2d5+i) for i in (0,1)] == [0x0bf080,syms['mixhook']], 'installed mix hook'
    return OUT/'installed_A.mem'


def run(remix, image):
    os.environ['REMIX'] = remix
    # The regular assembler also enforces no-REP, label safety and roundtrip.
    from build_bus import assemble_syms
    OUT.mkdir(parents=True,exist_ok=True)
    source = (ROOT/'modules/returns/returns.asm').read_text()
    image_mem = installed(remix,image,source,assemble_syms)
    codea,a = assemble_syms(source.replace('@RETURNS_CORE_GUARD@','; payload A'),0x10000,'RETURNS A')
    codeb,b = assemble_syms(source.replace('@RETURNS_CORE_GUARD@','rts'),0x11000,'RETURNS B')
    codew,w = assemble_syms(wrapper(a,b),0x1f000,'RETURNS test wrapper')
    rows,names = fixtures()
    mem = image_mem.read_bytes()
    base = mem[:-9]+record(0,0x10000,codea)+record(0,0x11000,codeb)+record(0,0x1f000,codew)
    base += record(1,0x10000,[v for row in rows for v in row])
    base += record(2,0x10000,[0]*(len(rows)*STRIDE)) + mem[-9:]
    patched=OUT/'probe.mem';patched.write_bytes(base)
    output=OUT/'observed.raw'
    command=[str(send_probe.HOST),'-mem',str(patched),'-init',f"{w['boot']:x}",
             '-proc',f"{w['step']:x}",'-frames','16','-blocks',str(len(rows)),
             '-alloc','1','-r7','2','-audio','80','-inmask','0',
             '-dumpy',f'10000,{0x10000+len(rows)*STRIDE:x},{output}']
    p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=60)
    (OUT/'probe.log').write_text(p.stdout+p.stderr)
    if p.returncode: raise RuntimeError((p.stdout+p.stderr)[-3000:])
    observed=list(struct.unpack('<'+'I'*(len(output.read_bytes())//4),output.read_bytes()))
    for i,(name,row) in enumerate(zip(names,rows)):
        expected=model(row); got=observed[i*STRIDE:(i+1)*STRIDE]
        if got != expected:
            diffs=[(j,hex(x),hex(y)) for j,(x,y) in enumerate(zip(expected,got)) if x!=y]
            raise AssertionError(f'{name}: expected/actual offsets {diffs[:12]}')
    # Positive control: the oracle must refuse a missing return contribution.
    active=names.index('mix-1-0-True-True')
    poisoned=observed[active*STRIDE:(active+1)*STRIDE]
    poisoned[440:472]=rows[active][440:472]
    assert poisoned != model(rows[active]), 'vacuous output oracle'
    receipt=dict(cases=len(rows),samples_exact=len(rows)*32,
                 coverage=['installed module bytes and hook','all 128 gains','bipolar/clipped MAIN and MASTER',
                           'all eight delay rotations','fresh/stale/consumed stamps',
                           'off-track init and proc','payload B no-op'],
                 limits='module instructions in DSP interpreter; full firmware and hardware timing separate')
    (OUT/'results.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(f'[ok] RETURNS: {len(rows)} exact DSP cases; gain, MAIN/MASTER, freshness, rotations, track/core guards')


def main():
    remix = sys.argv[1] if len(sys.argv)>1 else 'test/send-return-poc'
    if 'RETURNS' not in registry.remix(remix).modules:
        print('[ -- ] no RETURNS');return
    run(remix, ROOT/'out/mainos_bus.bin')


if __name__ == '__main__': main()
