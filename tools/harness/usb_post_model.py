#!/usr/bin/env python3
"""USB LAYOUT TRACKS POST's arithmetic in Python: core 0's per-track MAIN
gain and its 16-sample ramp (payload A P:0xfa-0x165, P:0x203-0x237) with
MAIN_LEVEL fixed at 64.

Measured under the port (5 Oct 2026): this integer model reproduced core 0's
MAIN target (0x16c78e at LEVEL 108, XLV unlocked, MAIN_LEVEL 64) and its
ramped outputs to the LSB. tools/verify/verify_usb_post.py and
tools/verify/verify_usb.py drive it.
"""


def s24(v):
    v &= 0xffffff
    return v - (1 << 24) if v & 0x800000 else v


def sq(w):
    """(w/32768)^2 in Q23 as core 0 squares the 16-bit word: mpy of w << 8 by
    itself, a1, the store limiting 2^23."""
    w &= 0xffff
    if w & 0x8000:
        w -= 0x10000
    return min((w * w) >> 7, 0x7fffff)


def target(w_main, w_xlv, xlv_table):
    """G: sq(MAIN word) times the XLV curve through core 0's mpy by
    (64/128)^2, i.e. floor(T / 4), then mpy again: floor(sq * T/4 / 2^23)."""
    t4 = xlv_table[(w_xlv >> 7) & 0xff] >> 2
    return (sq(w_main) * t4) >> 23


class Ramp:
    """One track's MAIN-gain ramp state: cur, the running increment, the
    last block's split."""

    def __init__(self, cur=0, inc=0, split=0):
        self.cur, self.inc, self.split = cur, inc, split

    def block(self, g, split):
        """Sixteen gains for one block toward target g with this block's split."""
        s = split & 15
        m = min(s, self.split)
        out = []
        cur = self.cur
        for _ in range(m):
            out.append(cur)
            cur += self.inc
        out += [cur] * (s - m)
        inc = (g - cur) >> 4
        for _ in range(16 - s):
            out.append(cur)
            cur += inc
        self.cur, self.inc, self.split = cur, inc, s
        return out


def stem(g, x):
    """The track's term of core 0's MAIN sum at the asl #2: floor(8 g x / 2^24)."""
    return (g * x) >> 21
