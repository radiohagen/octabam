#!/usr/bin/env python3
"""STEMS via UP+REC, key by key under the port, on both panels.

    python3 tools/verify/verify_stems_menu.py [remix]      (default: stems)

Builds the remix and the fixtures (STEMS_TEMPLATE), then boots the image
twice under `ot_emu --interactive` on a copy of the one-track fixture card:
as an MKII (MAIN MENU = PROJ) and as an MKI (FUNC+MIXER). Each boot:
- the cursor walks the stock root categories (four, or five with BRAIN);
  STEMS is not among them; PROJECT's row count stays 15;
- SYSTEM opens and the cursor reaches OS UPGRADE, the recovery path; ENTER
  is never pressed there;
- UP+REC opens STEMS as its own WCREATE window (stems_win) on REC — not
  MAIN MENU; NO closes it; UP+REC again toggles it closed;
- DOWN lands on T1 and UP on REC (status row skipped); DOWN reaches 24 BIT
  and stays (cursor never on PEAK), with the pane pinned so PEAK is still
  visible (STEM_REC.md 16.1);
- every track row turned off in turn leaves T8 on; with MAIN on, T8 can go
  off and MAIN can't; the three switches flip and say so; T3 off, then
  every other track on again;
- every STEMS label fits the window row (≤ 24 W of the small UI font);
- REC arms (CANCEL, ARMED) and cancels (REC, READY), then arms;
- with STEMS closed, PLAY; UP+REC shows STOP and REC mm:ss, and a key
  later the seconds have moved on; T3 is locked;
- with STEMS closed, STOP; the take ends DONE, and its folder holds seven
  tracks and MAIN, T3's missing.
A PNG of the screen at each step goes to out/stems_runs/menu-<model>-*.png.
Pass or fail comes from memory, never from a picture.

What it cannot see: the unit's key timing, its card speed while STEMS
is open, and the MKII's hardware (flash A)."""
import json
import os
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1])); import toolpath  # noqa: E402,F401
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import verify_stems as vs  # noqa: E402
from stems_panel import MENU_FOCUS, MenuPort, diff_box  # noqa: E402

ROOT_DESC, PROJECT_DESC, SYSTEM_DESC, SEL = 0x400cbd8c, 0x400cbcac, 0x400cbd1c, 0x0c
OS_UPGRADE = 1                  # SYSTEM's row 1 (MAINMENU.md 2)
PROJECT_N = 15                  # stock PROJECT row count (unchanged)
ENTER, CLOSE = "yes", "no"
WORK = pathlib.Path("out/stems_runs")
ERRS = ["RING FULL", "PATH FAILED", "OPEN FAILED", "SAME MINUTE", "WRITE FAILED",
        "SEEK FAILED", "CLOSE FAILED", "TASK FAILED"]
TEXTS = (["REC", "CANCEL", "STOP", "SAVING", "READY", "ARMED", "NO CARD", "PEAK 0%", "PEAK 100%",
          "REC 60:00", "DONE 60:00"] + ERRS + [f"T{k} [{m}]" for k in range(1, 9) for m in "X "] + ["T8 MASTER"]
         + [f"{n} [{m}]" for n in ("MAIN", "CUE", "AB", "CD", "AB STEREO", "CD STEREO", "24 BIT") for m in "X "])


def texts(p, s):
    return [p.cstr(p.long(s["stems_rows"] + vs.ROW_LEN * k)) for k in range(vs.MENU_ROWS)]


def redraw(p):
    """Force a STEMS window redraw: DOWN then UP keeps REC selected."""
    p.press("down", settle=80)
    p.press("up", settle=80)


def stems_open(p, s):
    return p.long(s["stems_win"]) != 0 and p.long(s["stems_live"]) != 0


def sel(p, desc):
    return p.long(desc + SEL)


def on_rec(p, s):
    while sel(p, s["stems_list"]) > 0:
        p.press("up", settle=40)


def widths(p, s, model):
    """Every STEMS label fits the window row: painted at x=4 in a WINW
    window, same 24-W ceiling the stock list pane used (small UI font)."""
    scratch = s["stems_fpath"]
    label_at = s["stems_rows"]          # row 0's label pointer
    keep = p.long(label_at)
    on_rec(p, s)

    def box(text, sk):
        p.poke(sk, text.encode("latin1") + b"\0")
        p.poke(label_at, sk.to_bytes(4, "big"))
        redraw(p)
        return p.screen()

    empty = box("", scratch)
    clip = diff_box(empty, box("W" * 24, scratch + 64))
    over = []
    for i, t in enumerate(TEXTS):
        b = diff_box(empty, box(t, scratch if i % 2 == 0 else scratch + 64))
        if clip is None or b is None or b[1] > clip[1]:
            over.append((t, None if b is None else b[1]))
    p.poke(label_at, keep.to_bytes(4, "big"))
    redraw(p)
    vs.check(f"{model}: every STEMS text fits the window row (≤ 24 W)",
             clip is not None and not over,
             f"clip {clip[1] if clip else None}, over {over}")


def enter_stems(p, s, model):
    """UP + REC: open STEMS window on REC."""
    p.chord("up", "rec", settle=400)
    lst = s["stems_list"]
    vs.check(f"{model}: STEMS opens on REC",
             stems_open(p, s) and sel(p, lst) == 0
             and p.long(lst + 0x18) == s["stems_rows"]
             and p.long(PROJECT_DESC) == PROJECT_N,
             f"win {p.long(s['stems_win']):#x}, selection {sel(p, lst)}, "
             f"rows {p.long(lst + 0x18):#x}, live {p.long(s['stems_live'])}, "
             f"project {p.long(PROJECT_DESC)}")


def reopen_stems(p, s, model):
    """After NO / close: UP + REC opens STEMS again on REC."""
    lst = s["stems_list"]
    if stems_open(p, s) and sel(p, lst) == 0 and p.long(lst + 0x18) == s["stems_rows"]:
        return
    p.chord("up", "rec", settle=400)
    vs.check(f"{model}: STEMS reopens on REC",
             stems_open(p, s) and sel(p, lst) == 0
             and p.long(lst + 0x18) == s["stems_rows"],
             f"win {p.long(s['stems_win']):#x}, selection {sel(p, lst)}, "
             f"rows {p.long(lst + 0x18):#x}")


def walk(model, s, fx):
    card = WORK / f"menu-{model}.img"
    shutil.copyfile(fx["card"], card)
    with MenuPort(vs.IMAGE, card, fx["set"], fx["project"], model == "mkii",
                  log_path=WORK / f"menu-{model}.log") as p:
        def shot(name):
            p.png(WORK / f"menu-{model}-{name}.png")

        p.settle()
        p.open_menu()
        shot("root")
        root_n = p.long(ROOT_DESC)
        seen = [sel(p, ROOT_DESC)]
        for _ in range(root_n - 1):
            p.press("down")
            seen.append(sel(p, ROOT_DESC))
        shot("root-last")
        vs.check(f"{model}: MAIN MENU opens on the root and the cursor walks {root_n} categories",
                 p.long(MENU_FOCUS) == ROOT_DESC and seen == list(range(root_n)), f"{seen}")
        vs.check(f"{model}: PROJECT stays stock ({PROJECT_N} rows)",
                 p.long(PROJECT_DESC) == PROJECT_N, f"count {p.long(PROJECT_DESC)}")
        # SYSTEM is always root selection 1 (PROJECT=0, SYSTEM=1, ...).
        while sel(p, ROOT_DESC) != 1:
            p.press("up")
        p.press(ENTER)
        p.press("down")
        shot("os-upgrade")
        vs.check(f"{model}: SYSTEM opens and the cursor reaches OS UPGRADE",
                 p.long(MENU_FOCUS) == SYSTEM_DESC and sel(p, SYSTEM_DESC) == OS_UPGRADE,
                 f"focus {p.long(MENU_FOCUS):#x}, selection {sel(p, SYSTEM_DESC)}")
        p.press(CLOSE, settle=100)                      # leave MAIN MENU

        enter_stems(p, s, model)
        shot("stems")
        vs.check(f"{model}: STEMS is its own window (MAIN MENU focus stays off stems_list)",
                 p.long(MENU_FOCUS) != s["stems_list"],
                 f"focus {p.long(MENU_FOCUS):#x}")

        p.press("down")
        down = sel(p, s["stems_list"])
        p.press("up")
        up = sel(p, s["stems_list"])
        vs.check(f"{model}: DOWN from REC lands on T1 and UP from T1 on REC", (down, up) == (vs.ROW_TRK0, 0),
                 f"{(down, up)}")
        walked = []
        for _ in range(16):
            p.press("down")
            walked.append(sel(p, s["stems_list"]))
        shot("last")
        last = 16
        vs.check(f"{model}: DOWN reaches 24 BIT and stays there, never on the PEAK row",
                 walked == list(range(vs.ROW_TRK0, last + 1)) + [last], f"{walked}")
        top = p.long(s["stems_list"] + 0x04)
        vs.check(f"{model}: at 24 BIT the pane shows PEAK (last row visible, not selected)",
                 sel(p, s["stems_list"]) == last
                 and top == vs.MENU_ROWS - vs.MENU_VISIBLE
                 and top <= vs.ROW_PEAK < top + vs.MENU_VISIBLE,
                 f"sel {sel(p, s['stems_list'])}, top {top}, peak {vs.ROW_PEAK}")
        # Pixel check: PEAK must paint inside the panel, not a clipped sliver.
        # Blank / restore the PEAK label; UP then DOWN redraws and re-pins on 24 BIT
        # (redraw()'s DOWN/UP would leave CD STEREO selected).
        def redraw_peak_row():
            p.press("up", settle=80)
            p.press("down", settle=80)

        peak_ptr = s["stems_rows"] + vs.ROW_LEN * vs.ROW_PEAK
        peak_keep = p.long(peak_ptr)
        scratch = s["stems_fpath"]
        p.poke(scratch, b"\0")
        p.poke(peak_ptr, scratch.to_bytes(4, "big"))
        redraw_peak_row()
        empty_peak = p.screen()
        p.poke(scratch, b"PEAK 0%\0")
        redraw_peak_row()
        peak_box = diff_box(empty_peak, p.screen())
        p.poke(peak_ptr, peak_keep.to_bytes(4, "big"))
        redraw_peak_row()
        # Panel y grows downward; PEAK is the bottom list row. Full glyph ≥ 5 px,
        # and clear of the window frame (bottom ink ≤ 58 on a 64-tall panel).
        vs.check(f"{model}: PEAK ink is on-screen (not clipped at the window bottom)",
                 peak_box is not None and peak_box[3] - peak_box[2] >= 5
                 and peak_box[3] <= 58,
                 f"box {peak_box}")
        for _ in range(last - vs.ROW_TRK0):
            p.press("up")                               # back to T1
        for k in range(8):                              # every track off in turn, T1 to T8
            p.press(ENTER)
            if k < 7:
                p.press("down")
        left = p.long(s["stems_tracks"]) & 0xFF
        vs.check(f"{model}: turning every track off leaves the last one on", left == 0x80, f"mask {left:#04x}")
        p.press("down")                                 # T8 -> MAIN (row 10)
        p.press(ENTER)                                  # MAIN on
        p.press("up")                                   # T8
        p.press(ENTER)                                  # T8 off: MAIN keeps a source
        p.press("down")                                 # MAIN
        p.press(ENTER)                                  # MAIN off: refused, the last source
        left = p.long(s["stems_tracks"]) & 0xFFF
        vs.check(f"{model}: with MAIN on, T8 can go off, and the last source stays on",
                 left == 0x100, f"sources {left:#05x}")
        p.press("up")                                   # T8
        p.press(ENTER)                                  # T8 on again; MAIN stays on for the take
        for _ in range(7):
            p.press("down")                             # T8 (row 9) -> 24 BIT (row 16)
        p.press(ENTER)
        p.press(ENTER)                                  # 24 BIT on, then off
        p.press("up")                                   # CD STEREO (row 15)
        p.press(ENTER)                                  # off
        fmt = p.long(s["stems_fmt"]) & 7
        t = texts(p, s)
        vs.check(f"{model}: the switches flip and say so",
                 fmt == 0b010 and t[14:17] == ["AB STEREO [X]", "CD STEREO [ ]", "24 BIT [ ]"],
                 f"fmt {fmt:03b}, {t[14:17]}")
        p.press(ENTER)                                  # CD STEREO on again
        for _ in range(6):
            p.press("up")                               # CD STEREO (row 15) -> T8 (row 9)
        shot("tracks-off")
        for _ in range(7):
            p.press("up")                               # T8 -> T1
        for k in range(7):
            if k != 2:
                p.press(ENTER)
            p.press("down")
        t = texts(p, s)
        mask = p.long(s["stems_tracks"]) & 0xFF
        trows = t[vs.ROW_TRK0:vs.ROW_TRK0 + 8]
        vs.check(f"{model}: T3 off, every other track on, the rows say so",
                 mask == 0xFB and trows == [f"T{k} [{' ' if k == 3 else 'X'}]" for k in range(1, 9)],
                 f"mask {mask:#04x}, {trows}")
        for _ in range(8):
            p.press("up")                               # T8 -> T1, then REC

        widths(p, s, model)                             # while STEMS is open, on its row paint

        p.press(ENTER)
        a = texts(p, s)[:2] + [p.long(s["stems_state"])]
        p.press(ENTER)
        c = texts(p, s)[:2] + [p.long(s["stems_state"])]
        p.press(ENTER)
        shot("armed")
        vs.check(f"{model}: REC arms and cancels", a == ["CANCEL", "ARMED", vs.ST_ARMED]
                 and c == ["REC", "READY", vs.ST_IDLE] and p.long(s["stems_state"]) == vs.ST_ARMED,
                 f"{a}, {c}")

        p.press(CLOSE, settle=100)                      # NO closes the STEMS window
        vs.check(f"{model}: NO closes the STEMS window",
                 not stems_open(p, s),
                 f"win {p.long(s['stems_win']):#x}, live {p.long(s['stems_live'])}")

        enter_stems(p, s, model)
        p.chord("up", "rec", settle=400)                # UP+REC toggles closed
        vs.check(f"{model}: UP+REC toggles STEMS closed",
                 not stems_open(p, s),
                 f"win {p.long(s['stems_win']):#x}, live {p.long(s['stems_live'])}")

        p.press("play", settle=1500)
        reopen_stems(p, s, model)
        t0 = texts(p, s)
        before = p.screen()
        shot("recording")
        p.run(2500, wall=30)
        redraw(p)
        t1 = texts(p, s)
        after = p.screen()
        shot("recording-later")
        vs.check(f"{model}: reopened on STEMS: STOP and REC mm:ss, and a key later the seconds moved on",
                 stems_open(p, s) and p.long(s["stems_list"] + 0x18) == s["stems_rows"]
                 and t0[0] == "STOP" and t0[1].startswith("REC ")
                 and t1[1].startswith("REC ") and t1[1] > t0[1] and diff_box(before, after) is not None,
                 f"{t0[:2]} -> {t1[:2]}")
        for _ in range(3):
            p.press("down")                             # REC -> T1 -> T2 -> T3
        p.press(ENTER)
        vs.check(f"{model}: T3 is locked while it records",
                 p.long(s["stems_tracks"]) & 0xFF == 0xFB and texts(p, s)[vs.ROW_TRK0 + 2] == "T3 [ ]")
        p.press(CLOSE, settle=100)
        vs.check(f"{model}: NO closes STEMS while recording",
                 not stems_open(p, s),
                 f"win {p.long(s['stems_win']):#x}")
        p.press("stop", settle=500)
        for _ in range(60):
            if p.long(s["stems_state"]) == vs.ST_IDLE:
                break
            p.run(500, wall=5)
        reopen_stems(p, s, model)
        t = texts(p, s)
        shot("done")
        vs.check(f"{model}: after STOP: IDLE, REC and DONE mm:ss",
                 p.long(s["stems_state"]) == vs.ST_IDLE and t[0] == "REC" and t[1].startswith("DONE "),
                 f"state {p.long(s['stems_state'])}, {t[:3]}")
        p.card_flush()
    names = [n.upper() for n, _ in vs.take_files(str(card))]
    vs.check(f"{model}: the take holds seven tracks and MAIN, T3's missing",
             names == ["MAIN.WAV"] + [f"T{k}.WAV" for k in (1, 2, 4, 5, 6, 7, 8)], f"{names}")


def main():
    from remix import registry
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    name = args[0] if args else "stems"
    if "STEM REC" not in registry.remix(name).modules:
        print(f"  [ -- ] {name} does not carry STEM REC -- nothing to check")
        return 0
    env = {**os.environ, "REMIX": name, "XBUS": "1", "SPEC": "1"}
    r = subprocess.run([sys.executable, "tools/build/build_bus.py"], capture_output=True, text=True, env=env)
    if r.returncode:
        tail = (r.stdout + r.stderr).strip().splitlines()
        sys.exit(f"{name}: build failed: {tail[-1] if tail else '?'}")
    if not vs.EMU.exists():
        print("  [SKIP] the menu under the port: build the port (make emu-cf)")
        return 0
    if not vs.TEMPLATE.is_dir():
        print(f"  [SKIP] the menu under the port: no project template at {vs.TEMPLATE} (STEMS_TEMPLATE=<dir>)")
        return 0
    if not vs.fixtures():
        return 1
    s = vs.syms()
    fx = json.loads(vs.FIXTURE.read_text())
    WORK.mkdir(parents=True, exist_ok=True)
    for model in ("mkii",) if "--mkii" in sys.argv else ("mkii", "mki"):    # --mkii: a development switch
        walk(model, s, fx)
    return 1 if vs.fails else 0


if __name__ == "__main__":
    sys.exit(main())
