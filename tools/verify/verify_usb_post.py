#!/usr/bin/env python3
"""USB AUDIO OUT TRACKS POST against core 0's own MAIN, under the ColdFire port.

Stages the tone project (tools/harness/usb_sig_project.py: every track
plays its own steady tone) on a card, as tools/harness/usb_align.py does,
boots the image under test (out/mainos_bus.bin) with both DSP cores live,
makes the producer run with no host (aud_force), and drives the gain
controls while every relevant write is logged with its sample time:

  LEVEL (CC 46 and the knob byte), mute (CC 49), solo (CC 50), XLV (a scene
  lock on one track, then the crossfader), the split word (a sample offset
  in the block, which makes core 0's ramp three segments), several at once,
  and, in a second run, MASTER TRACK.

Per producer block F (the stems written at the end of frame F):

  1. SUM: core 0's MAIN that arrives at frame F+1 is the mix of the block the
     producer read at F (MAIN lags the tracks one block: usb_align). At
     MAIN_LEVEL 64 (set here) the factor POST leaves out is 1, so MAIN equals
     the sum of the stems up to the per-stem truncations: MAIN - sum in
     [0, 7] on every sample, both sides. (MASTER TRACK off; every track's
     LEVEL is brought down first so the stock mix never saturates.)
  2. MODEL: every stem and every block's ramp state equal
     tools/harness/usb_post_model.py's, from the read-back block the producer
     read (reassembled from the logged writes), the snapshot built at frame
     F-4 and the ramp state the unit logged after F-1.
  3. PAIRING: the same model with the snapshot of F-3 or F-5 breaks check 1
     somewhere in the run -- the events do exercise the pairing.
  4. MASTER TRACK: MAIN (T8 alone) equals T8's stem exactly.

    tools/verify/verify_usb_post.py [--source <project>] [--keep DIR]

The source project is the template usb_sig_project.py needs (a locally saved
Octatrack project; default OT_PROJECT or ~/.octabam_project). SKIPs without
it, the port (make emu-cf) or the .venv, or when the image under test does not
carry USB AUDIO OUT TRACKS POST.
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/harness"))
import toolpath  # noqa: E402,F401
import usb_post_model as M  # noqa: E402

EMU = ROOT / "out/emu/ot_emu"
PY = ROOT / ".venv/bin/python3"
IMAGE = ROOT / "out/mainos_bus.bin"
ELF = ROOT / "out/platform/runtime/runtime.elf"
PING, PREV = 0x800000e0, 0x800000e4   # this frame's read-back bank, and the one the producer reads
ARENA, ARENA_LEN = 0x80003190, 0x800   # the read-back arena, two banks (usbaudio.s RB_BASE)
SNAP, SNAP_LEN = 0x80005460, 0x200     # the gain snapshot ring
MAINB = 0x80005e60                     # MAIN, 16 x (L,R) a frame (usbaudio.s MAIN_CUE_BASE)
C50 = 0x80000c50                       # [LEVEL, CUE] knob bytes per track
XLV_LOCKS = 0x800010d4                 # [A, B] scene XLV lock bytes per track
SPLITS = 0x8000485a                    # + 8t: the split word the snapshot copies
MASTER_ON = 0x80000034                 # MASTER TRACK
MAIN_LEVEL = 0x80000035
AUDIO_CC_IN = 0x80000049
LEVEL_START = 80                       # (80/128)^2: eight tones at -12 dBFS sum under full scale
SLOT = 64


class Emu:
    def __init__(self, args, log):
        self.p = subprocess.Popen([str(EMU)] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=ROOT)
        self.log = open(log, "w")
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError(f"ot_emu exited before `ready` ({log})")
            self.log.write(l)
            if l.startswith("ready"):
                break

    def cmd(self, c):
        self.p.stdin.write(c + "\n")
        self.p.stdin.flush()
        r = self.p.stdout.readline().rstrip("\n")
        self.log.write(f"> {c}\n{r[:300]}\n")
        if r.startswith("err"):
            raise RuntimeError(f"{c}: {r}")
        return r

    def poke(self, addr, data):
        self.cmd(f"poke {addr:#x} {bytes(data).hex()}")

    def peek(self, addr, n):
        return bytes.fromhex(self.cmd(f"peek {addr:#x} {n}").split()[1])

    def close(self):
        try:
            self.cmd("quit")
        except Exception:
            pass
        self.p.wait(timeout=60)


def stage(source, work):
    """The tone project on a card image; returns the ot_emu card arguments."""
    proj = work / "project"
    r = subprocess.run([str(PY), "tools/harness/usb_sig_project.py", "--source", str(source), "--out", str(proj)],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"verify_usb_post: usb_sig_project failed\n{r.stdout[-800:]}{r.stderr[-800:]}")
    # MASTER TRACK off: MAIN is then the plain mix (the second run turns it on live)
    pw = proj / "project.work"
    pw.write_bytes(pw.read_bytes().replace(b"MASTER_TRACK=1", b"MASTER_TRACK=0"))
    card = work / "card.img"
    cmd = [str(PY), str(ROOT / "tools/emu/ot_emu/stage_card.py"), str(proj), "OCTABAM", "USBSIG",
           "--tree", str(work / "tree"), "--out", str(card), "--image-mb", "64"]
    for t in range(1, 9):
        cmd += ["--audio", f"{proj / 'AUDIO' / 'USBSIG' / f'T{t}.wav'}:AUDIO/USBSIG/T{t}.wav"]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"verify_usb_post: stage_card failed\n{r.stdout[-800:]}{r.stderr[-800:]}")
    # --mount: the port posts LOAD PROJECT in its boot, as tools/panel does
    return ["--card", str(card), "--mount", "--set", "OCTABAM", "--project", "USBSIG", "--load-ms", "90000"]


def xlv_table_from_elf(sym):
    """post_xlv as linked (what the unit multiplies by)."""
    out = subprocess.run(["m68k-elf-objdump", "-s", f"--start-address={sym['post_xlv']:#x}",
                          f"--stop-address={sym['post_xlv'] + 1024:#x}", str(ELF)],
                         capture_output=True, text=True).stdout
    words = []
    for line in out.splitlines():
        parts = line.split()
        try:
            at = int(parts[0], 16)
        except (IndexError, ValueError):
            continue
        if sym["post_xlv"] <= at < sym["post_xlv"] + 1024:
            words += [int(x, 16) for x in parts[1:5] if len(x) == 8]
    return words[:256]


def session(sym, card, events, total_ms, workdir, tag, master=False):
    """One port run: load, play, watch, apply `events` [(ms, fn)], return the frames."""
    e = Emu(["--image", str(IMAGE), "--interactive", "--dsp"] + card, workdir / f"port_{tag}.log")
    try:
        e.cmd("frame on")
        e.poke(sym["aud_force"], [1])
        e.poke(MAIN_LEVEL, [64])
        e.poke(AUDIO_CC_IN, [1])
        if master:
            e.poke(MASTER_ON, [1])
        for t in range(8):
            e.cmd(f"midi {0xb0 + t:02x} 2e {LEVEL_START:02x}")
        e.cmd("key 0x25 1")                      # PLAY, as the panel reports it
        e.cmd("run 20")
        e.cmd("key 0x25 0")
        e.cmd("run 400")
        for a, n in [(PING, 4), (PREV, 4), (ARENA, ARENA_LEN), (SNAP, SNAP_LEN), (MAINB, 0x80),
                     (sym["aud_ring"], 1024 * SLOT), (sym["post_state"], 96)]:
            e.cmd(f"watchmem {a:#x} {n}")
        t = 0
        for ms, fn in sorted(events, key=lambda x: x[0]) + [(total_ms, None)]:
            if ms > t:
                e.cmd(f"run {ms - t}")
                t = ms
            if fn:
                fn(e)
        w = e.cmd("writes").split()
    finally:
        e.close()
    return frames_of([x.split(":") for x in w[2:]], sym), int(w[1].split("=")[1])


def frames_of(rows, sym):
    """Group the writes into ColdFire frames (a frame starts at frame_isr's ping
    write). The read-back block the producer read in frame F is reassembled from
    the arena writes as they stood when its first ring write landed."""
    ring0, ring1 = sym["aud_ring"], sym["aud_ring"] + 1024 * SLOT
    st0 = sym["post_state"]
    arena = bytearray(ARENA_LEN)
    prev = None
    frames, cur = [], None
    for s, _pc, a, v, sz, _tcb in rows:
        A, V, sz = int(a, 16), int(v, 16), int(sz)
        if ARENA <= A < ARENA + ARENA_LEN:
            arena[A - ARENA:A - ARENA + sz] = V.to_bytes(sz, "big")
            continue
        if A == PREV:
            prev = V
            continue
        if A == PING:
            cur = {"t": float(s), "snap": {}, "main": {}, "ring": {}, "state": {}, "x": None}
            frames.append(cur)
            continue
        if cur is None:
            continue
        if SNAP <= A < SNAP + SNAP_LEN:
            for i in range(0, sz, 2):            # a long store (studio mode's clrl) is two words
                cur["snap"][A + i] = (V >> (8 * (sz - 2 - i))) & 0xffff
        elif MAINB <= A < MAINB + 0x80:
            cur["main"][A - MAINB] = V
        elif ring0 <= A < ring1:
            if cur["x"] is None and prev is not None:
                b = prev * 1024
                cur["x"] = [[[int.from_bytes(arena[b + t * 128 + j * 8 + c * 4:b + t * 128 + j * 8 + c * 4 + 4],
                                             "big", signed=True) >> 8 for j in range(16)] for c in range(2)]
                            for t in range(8)]
            cur["ring"][A - ring0] = V
        elif st0 <= A < st0 + 96:
            cur["state"][A - st0] = V
    return frames


def s32(v):
    return v - (1 << 32) if v & 0x80000000 else v


def analyse(frames, xlv, master=False):
    """Per-block stems, MAIN, model; returns the result lines and pass/fail."""
    snaps = []
    for f in frames:
        ent = {}
        for a, v in f["snap"].items():
            k, off = (a - SNAP) // 0x80, (a - SNAP) % 0x80
            ent.setdefault(k, {})[off] = v
        # the builder writes one entry per frame (tracks at +0..0x3f)
        snaps.append(max(ent.items(), key=lambda kv: sum(1 for o in kv[1] if o < 0x40))[1] if ent else {})
    prod = []
    for f in frames:
        if len(f["ring"]) < 256 or f["x"] is None:
            prod.append(None)
            continue
        base = min(f["ring"]) // SLOT * SLOT
        stems = [[[0] * 16 for _ in range(2)] for _ in range(8)]
        ok = True
        for j in range(16):
            for t in range(8):
                for c in range(2):
                    v = f["ring"].get(base + j * SLOT + t * 8 + c * 4)
                    if v is None:
                        ok = False
                        continue
                    stems[t][c][j] = M.s24(int.from_bytes(v.to_bytes(4, "big"), "little") >> 8)
        prod.append(stems if ok else None)
    mains = []
    for f in frames:
        m = f["main"]
        if len(m) < 64:
            mains.append(None)
            continue
        blk = [[0] * 16, [0] * 16]
        for j in range(16):
            for c in range(2):
                hi, lo = m.get(j * 8 + c * 4), m.get(j * 8 + c * 4 + 2, 0)
                blk[c][j] = M.s24(((hi << 16) | lo) >> 8) if hi is not None else None
        mains.append(blk)
    states = []
    for f in frames:
        st = f["state"]
        states.append(None if len(st) < 24 else
                      [(s32(st.get(12 * t, 0)), s32(st.get(12 * t + 4, 0)), st.get(12 * t + 8, 0)) for t in range(8)])

    def words(i, t):
        e = snaps[i]
        return e.get(8 * t + 2, 0), e.get(8 * t + 4, 0), e.get(8 * t + 6, 0)

    def model(F, lag):
        """The model's stems for block F with the snapshot of frame F-lag, from the
        logged state after F-1 and the block the producer read."""
        st = states[F - 1]
        if st is None or F - lag < 0:
            return None, None
        out, new = [], []
        for t in range(8):
            wm, wx, sp = words(F - lag, t)
            r = M.Ramp(*st[t])
            g = r.block(M.target(wm, wx, xlv), sp)
            new.append((r.cur, r.inc, r.split))
            out.append([[M.stem(g[j], frames[F]["x"][t][c][j]) for j in range(16)] for c in range(2)])
        return out, new

    lines, ok = [], True
    blocks = [F for F in range(8, len(frames) - 1) if prod[F] and mains[F + 1] and states[F - 1]]
    splits = sum(1 for F in blocks for t in range(8) if words(F - 4, t)[2] & 15)
    sounding = sum(1 for F in blocks for t in range(8) if any(prod[F][t][0]))
    lines.append(f"RUN: {len(blocks)} blocks; {sounding} track-blocks with signal; "
                 f"{splits} track-blocks with a nonzero split")
    ok &= bool(blocks) and sounding > 0 and (splits > 0 or master)    # the plain run pokes the split word
    bad_model = []
    for F in blocks:
        exp, new = model(F, 4)
        if exp is None:
            continue
        if exp != prod[F]:
            t = next(t for t in range(8) if exp[t] != prod[F][t])
            bad_model.append((F, t, exp[t][0][:4], prod[F][t][0][:4]))
        if states[F] and new != states[F]:
            bad_model.append((F, "state", new[:2], states[F][:2]))
    lines.append(f"MODEL: {len(blocks)} blocks x 8 tracks x 32 samples, stems and ramp state against "
                 f"usb_post_model with the snapshot of F-4: "
                 f"{'exact' if not bad_model else f'{len(bad_model)} mismatches, first {bad_model[:2]}'}")
    ok &= not bad_model
    if not master:
        diffs = []
        for F in blocks:
            for c in range(2):
                for j in range(16):
                    diffs.append(mains[F + 1][c][j] - sum(prod[F][t][c][j] for t in range(8)))
        bad = [d for d in diffs if not 0 <= d <= 7]
        lines.append(f"SUM: MAIN(F+1) - sum of the eight stems(F) over {len(diffs)} samples: "
                     f"min {min(diffs)} max {max(diffs)}, outside [0, 7]: {len(bad)}")
        ok &= bool(diffs) and not bad
        for lag in (3, 5):
            nbad = 0
            for F in blocks:
                exp, _ = model(F, lag)
                if exp is None:
                    continue
                for c in range(2):
                    for j in range(16):
                        d = mains[F + 1][c][j] - sum(exp[t][c][j] for t in range(8))
                        nbad += not 0 <= d <= 7
            lines.append(f"PAIRING: with the snapshot of F-{lag} instead, {nbad} samples fall outside [0, 7]"
                         + (" (the events exercise the pairing)" if nbad else " -- the run does not exercise it"))
            ok &= nbad > 0
    else:
        diffs = [mains[F + 1][c][j] - prod[F][7][c][j] for F in blocks for c in range(2) for j in range(16)]
        bad = [d for d in diffs if d != 0]
        lines.append(f"MASTER: MAIN(F+1) - T8 stem(F) over {len(diffs)} samples: "
                     f"min {min(diffs)} max {max(diffs)}, nonzero: {len(bad)}")
        ok &= bool(diffs) and not bad
    return lines, ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=os.environ.get("OT_PROJECT") or
                    (pathlib.Path("~/.octabam_project").expanduser().read_text().strip()
                     if pathlib.Path("~/.octabam_project").expanduser().is_file() else ""))
    ap.add_argument("--keep", help="keep the staged card and the port logs here")
    a = ap.parse_args()
    if not a.source:
        print("  [SKIP] verify_usb_post: no source project (OT_PROJECT=<dir> or ~/.octabam_project)")
        return 0
    if not EMU.is_file() or not PY.is_file():
        print("  [SKIP] verify_usb_post: needs the port (make emu-cf) and the .venv")
        return 0
    if not IMAGE.is_file() or not ELF.is_file():
        print("  [FAIL] verify_usb_post: no out/mainos_bus.bin / runtime.elf (make bus)")
        return 1
    nm = subprocess.run(["m68k-elf-nm", str(ELF)], capture_output=True, text=True).stdout
    sym = {p[2]: int(p[0], 16) for p in (l.split() for l in nm.splitlines()) if len(p) == 3}
    if "post_xlv" not in sym:
        print("  [SKIP] verify_usb_post: the image under test does not carry LAYOUT TRACKS POST")
        return 0
    work = pathlib.Path(a.keep) if a.keep else pathlib.Path(tempfile.mkdtemp(prefix="usb_post_"))
    work.mkdir(parents=True, exist_ok=True)
    card = stage(a.source, work)
    xlv = xlv_table_from_elf(sym)
    if len(xlv) != 256 or xlv[254] < 0x7f0000:
        print(f"  [FAIL] verify_usb_post: post_xlv not read back from {ELF}")
        return 1

    midi = lambda h: (lambda e: e.cmd("midi " + h))
    poke = lambda addr, data: (lambda e: e.poke(addr, data))
    key = lambda b: (lambda e: e.cmd(f"key 0x40 {b}"))
    events = [
        (8, midi("b0 2e 36")),                       # T1 LEVEL 80 -> 54 over CC 46
        (24, midi("b1 31 7f")),                      # T2 mute
        (34, midi("b1 31 00")),                      # T2 unmute
        (44, midi("b2 32 7f")),                      # T3 solo: every other MAIN word 0
        (52, midi("b2 32 00")),                      # unsolo
        (60, poke(XLV_LOCKS + 2 * 3, [127, 0])),     # T4 XLV locked: A 127, B 0
        (66, key(255)),                              # crossfader to A: T4 XLV 0x7f00
        (72, key(1)),                                # to B: 0
        (78, key(129)),                              # back to the middle
        (84, poke(SPLITS + 8 * 5, [0, 7])),          # T6 split 7
        (85, poke(C50 + 2 * 5, [30])),               # and T6 LEVEL -> 30: a ramp with a split
        (97, poke(SPLITS + 8 * 5, [0, 3])),          # split 3 under the running ramp
        (99, midi("b5 31 7f")),                      # T6 mute mid-ramp
        (104, poke(SPLITS + 8 * 5, [0, 12])),
        (106, midi("b5 31 00")),                     # unmute, split 12
        (112, poke(SPLITS + 8 * 5, [0, 0])),
        (114, midi("b4 31 7f")),                     # T5 mute and T7 LEVEL at once
        (114, midi("b6 2e 7f")),
        (122, midi("b4 31 00")),
    ]
    ok = True
    frames, nwrites = session(sym, card, events, 135, work, "plain")
    lines, pok = analyse(frames, xlv)
    print(f"verify_usb_post: {len(frames)} frames logged ({nwrites} writes)")
    for l in lines:
        print("  " + l)
    ok &= pok
    mframes, _ = session(sym, card, [(10, midi("b7 2e 50")), (20, midi("b7 31 7f")), (28, midi("b7 31 00"))],
                         40, work, "master", master=True)
    mlines, mok = analyse(mframes, xlv, master=True)
    for l in mlines:
        print("  " + l)
    ok &= mok
    print(f"  [{'PASS' if ok else 'FAIL'}] USB AUDIO OUT TRACKS POST: the stems are core 0's per-track MAIN terms (logs: {work})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
