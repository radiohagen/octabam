#!/usr/bin/env python3
"""Decode CF METER's readout (modules/cfmeter) from a capture of track 8.

    python3 tools/harness/cfmeter.py capture.wav [--lr 14,15]   # USB audio: T8 = channels 15/16
    python3 tools/harness/cfmeter.py --dump out/setverify/port.dump   # the port's read-back blocks

The insert prints a square wave per 16-sample block: L = N x 128, R =
8192 x 128 (24-bit units), so N = 8192 x |L| / |R| per block, whatever
the gain after the slot. N steps through sixteen slots, 125 ms each, the
first 0 (the sync) and the second 8192. Slots 2..7 are the ColdFire's
(DMA timer 3 at 132 MHz): idle %, the frame interrupt's mean and longest
duration and the frame period in microseconds (16 / 44,100 s = 362.8 us
checks the rate), the idle loop's shortest step in timer counts, BURN in
microseconds. Slots 8..15 are core 0's own, over the 2 s window before
slot 8: the spin count of the wait for the next frame (min / max, polls),
ESAI underrun (TUE) and overrun (ROE) frames and ESAI_1's, the frame
period on the DSP's timer 0 (min / max, microseconds at CLK/2 = 99.95
MHz; 362.8 us nominal) and the frames in the window (5,512 nominal).

An analog capture of T8 (CUE into an interface, USB cable out) carries a
little DC and crosstalk on L: the sync slot reads ~6-30, not ~0, and the
sync -> reference step smears over a few blocks. --analog widens the edge
finder (sync < 60, up to 8 blocks before the reference, cycles closer
than 2,000 blocks dropped); --sync-max / --sync-back / --min-cycle set the
three on their own. (Bryan T, 4 Oct 2026.)

The ISR mean alternates between consecutive 2 s cycles on a playing unit
(a 4 s period), so the summary also prints the two phases' means and
their average, which an odd number of cycles would otherwise lean.
"""
import argparse, math, statistics, sys, wave
import numpy as np

CLK = 132e6
DSPCLK2 = 199.9e6 / 2            # timer 0 counts at CLK/2 (docs/firmware/CHIP.md: 199.9 MHz measured)
REF = 8192
SLOTS = 16


def load_wav(path, lr):
    w = wave.open(path)
    n, ch, sw = w.getnframes(), w.getnchannels(), w.getsampwidth()
    raw = w.readframes(n); w.close()
    if sw == 2:
        x = np.frombuffer(raw, np.int16).astype(float) / 32768
    elif sw == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
        x = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        x = np.where(x >= 1 << 23, x - (1 << 24), x) / float(1 << 23)
    else:
        x = np.frombuffer(raw, np.int32).astype(float) / 2 ** 31
    x = x.reshape(-1, ch)
    return x[:, lr[0]], x[:, lr[1]]


def load_dump(path):
    """Track 8 from the port's read-back blocks (RB_BASE + bank*1024 +
    track*128 + frame*8, 32-bit L,R): the core-0 classes at 0x80003390 and
    0x80003790 hold tracks 5-8."""
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    import blockdump
    blocks = [(f, w) for d, f, ch, core, ram, w in blockdump.read(path)
              if d == "<" and ch == 1 and core == 0 and ram in (0x80003390, 0x80003790)]
    blocks.sort()
    L, R = [], []
    for _, w in blocks:
        seg = w[192:256]
        v = [(seg[2 * i] << 16 | seg[2 * i + 1]) for i in range(32)]
        v = [(x - (1 << 32) if x >= 1 << 31 else x) / 2 ** 31 for x in v]
        L += v[0::2]; R += v[1::2]
    return np.array(L), np.array(R)


def per_block(L, R, n=16):
    m = len(L) // n
    l = np.sqrt(np.mean(L[:m * n].reshape(m, n) ** 2, axis=1))
    r = np.sqrt(np.mean(R[:m * n].reshape(m, n) ** 2, axis=1))
    return np.where(r > 1e-6, REF * l / np.maximum(r, 1e-9), np.nan)


def cycles(nb, sync_max=20, sync_back=2, min_cycle=0):
    """Each cycle starts where N steps from the sync (~0) to the reference
    (8192); its sixteen slots are one sixteenth of the distance to the next
    such edge each, read as the median of each slot's middle half."""
    ok = ~np.isnan(nb)
    ref = ok & (np.abs(nb - REF) < 0.01 * REF)
    sync = ok & (np.abs(nb) < sync_max)
    # On the unit's USB stream one block can straddle the slot change, so
    # the sync may sit two blocks back; an analog capture smears it further.
    edges = [i for i in range(sync_back, len(nb))
             if ref[i] and not ref[i - 1] and any(sync[i - j] for j in range(1, sync_back + 1))]
    if min_cycle:                       # a dip in the reference slot splits a cycle
        kept = []
        for e in edges:
            if not kept or e - kept[-1] >= min_cycle:
                kept.append(e)
        edges = kept
    rows = []
    for e0, e1 in zip(edges, edges[1:]):
        seg = (e1 - e0) / SLOTS
        row = []
        for k in range(SLOTS):
            a = e0 + int((k - 1 + 0.25) * seg) if k else e0 - int(0.75 * seg)
            b = e0 + int((k - 1 + 0.75) * seg) if k else e0 - int(0.25 * seg)
            row.append(float(np.nanmedian(nb[max(a, 0):b])))
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wav", nargs="?")
    ap.add_argument("--lr", default="14,15", help="0-based channel indices of T8 L,R in the file")
    ap.add_argument("--dump", help="a ot_emu --block-dump file instead of a capture")
    ap.add_argument("--analog", action="store_true", help="an analog capture of T8: --sync-max 60 --sync-back 8 --min-cycle 2000")
    ap.add_argument("--sync-max", type=float, default=None, help="a block reads as the sync below this N (default 20)")
    ap.add_argument("--sync-back", type=int, default=None, help="blocks before the reference edge the sync may sit (default 2)")
    ap.add_argument("--min-cycle", type=int, default=None, help="edges closer than this many blocks are one cycle (default 0)")
    a = ap.parse_args()
    if a.dump:
        L, R = load_dump(a.dump)
    else:
        L, R = load_wav(a.wav, tuple(int(v) for v in a.lr.split(",")))
    nb = per_block(L, R)
    d = (60, 8, 2000) if a.analog else (20, 2, 0)
    rows = cycles(nb, a.sync_max if a.sync_max is not None else d[0],
                  a.sync_back if a.sync_back is not None else d[1],
                  a.min_cycle if a.min_cycle is not None else d[2])
    if not rows:
        sys.exit("cfmeter: no sync -> reference edge pair found")
    us = lambda q: q * 4 / CLK * 1e6
    dus = lambda q: q * 4 / DSPCLK2 * 1e6
    print(f"{len(rows)} cycle(s) of 2 s; values are the medians of each 125 ms slot")
    print("ColdFire (slots 2-7)")
    print(f"{'idle %':>7} {'isr mean us':>11} {'isr max us':>10} {'period us':>9} {'isr %':>6} {'step cnt':>8} {'burn us':>7}")
    for r in rows:
        idle = r[2] / 16384 * 100
        per = us(r[5])
        print(f"{idle:7.2f} {us(r[3]):11.1f} {us(r[4]):10.1f} {per:9.1f} "
              f"{(us(r[3]) / per * 100 if per else float('nan')):6.1f} {r[6]:8.0f} {us(r[7]):7.1f}")
    print("DSP core 0 (slots 8-15, the 2 s window before each)")
    print(f"{'spin min':>8} {'spin max':>8} {'TUE':>5} {'ROE':>5} {'ESAI1':>5} {'per min us':>10} {'per max us':>10} {'frames':>6}")
    for r in rows:
        print(f"{r[8]:8.0f} {r[9]:8.0f} {r[10]:5.0f} {r[11]:5.0f} {r[12]:5.0f} "
              f"{dus(r[13]):10.1f} {dus(r[14]):10.1f} {r[15]:6.0f}")
    med = lambda j: statistics.median(r[j] for r in rows)
    print(f"median: idle {med(2) / 16384 * 100:.2f} %, isr mean {us(med(3)):.1f} us, "
          f"isr max {us(med(4)):.1f} us, period {us(med(5)):.1f} us (16/44100 s = 362.8 us); "
          f"spin min {med(8):.0f}, TUE {med(10):.0f}, ROE {med(11):.0f}, "
          f"DSP period {dus(med(13)):.1f}..{dus(med(14)):.1f} us, frames {med(15):.0f} (5,512 per 2 s)")
    if len(rows) >= 2:
        pa = statistics.mean(us(r[3]) for r in rows[0::2])
        pb = statistics.mean(us(r[3]) for r in rows[1::2])
        print(f"isr mean by phase (alternate cycles): {pa:.1f} / {pb:.1f} us, balanced {(pa + pb) / 2:.1f} us")


if __name__ == "__main__":
    main()
