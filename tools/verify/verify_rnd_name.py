#!/usr/bin/env python3
"""RND NAME under the port: FUNC+CUE on NAME THE NEW PROJECT fills
the editor buffer with YYMMDD + space + a joined pool name.

    python3 tools/verify/verify_rnd_name.py REMIX [--project DIR]

Opens PROJECT > CHANGE > CREATE EMPTY PROJECT under `--mkii`, holds FUNC
and taps CUE, then dumps the name buffer. Asserts `YYMMDD ` (pinned
RTC) plus a joined pool name. A second chord must change the words.

SKIPs without the port or a project. Rename is not exercised here (the
chord is gated on the create callback; that path is asserted by the
gate's create-only buffer fill).
"""
from __future__ import annotations

import argparse
import os
import pathlib
import struct
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import toolpath  # noqa: E402,F401
from remix import registry  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
EMU = ROOT / "out/emu/ot_emu"
PY = ROOT / ".venv/bin/python3"
OUT = ROOT / "out/rndname_verify"
BUF, CB, WIN, DISP = 0x460E436A, 0x460E761A, 0x460E7612, 0x460E743C
CREATE_CB = 0x400644F0

POOL_A = ('FOG', 'DUB', 'DARK', 'COLD', 'DRONE', 'SLEEP', 'WARE', 'ECHO', 'VOID', 'SUB', 'LATE', 'GRID', 'SOFT', 'DEEP', 'SLOW', 'MIST', 'RAW', 'WET', 'DRY', 'LOW', 'HI', 'DIM', 'WARM', 'THIN', 'THICK', 'SHARP', 'BLUNT', 'FAST', 'IDLE', 'LOUD', 'MUTE', 'NOISE', 'GLASS', 'IRON', 'RUST', 'DUST', 'ASH', 'SMOKE', 'STEAM', 'ICE', 'STONE', 'CLAY', 'BONE', 'WIRE', 'TAPE', 'FILM', 'VHS', 'CRT', 'NEON', 'ACID', 'BASE', 'PHASE', 'PULSE', 'SWEEP', 'GLIDE', 'SNAP', 'CLICK', 'THUMP', 'RUMBLE', 'CRACK', 'BLEED', 'GHOST', 'SHADOW', 'TRACE')
POOL_B = ('BED', 'LOOP', 'WASH', 'TAPE', 'CHAIN', 'VERB', 'SCENE', 'LOCK', 'HUM', 'PAD', 'GATE', 'YARD', 'HAZE', 'DRIFT', 'POOL', 'STEM', 'HIT', 'KICK', 'SNAR', 'CLAP', 'HAT', 'TOM', 'RIM', 'CLICK', 'BASS', 'LEAD', 'ARP', 'SEQ', 'FX', 'BUS', 'SEND', 'RET', 'ROOM', 'HALL', 'PLATE', 'SPRING', 'CAB', 'AMP', 'PEDAL', 'RACK', 'TAKE', 'CLIP', 'SHOT', 'PASS', 'RUN', 'CUE', 'DROP', 'RISE', 'SLOT', 'BANK', 'PART', 'PATT', 'KIT', 'SET', 'DIR', 'FILE', 'WAVE', 'BUF', 'RING', 'CORE', 'NODE', 'PORT', 'LANE', 'TRACK')
POOL = {a + b for a in POOL_A for b in POOL_B}
POOL_ONE = set(POOL_A) | set(POOL_B)
# 2026-10-14 12:00:00 UTC — --rtc Fixed epoch for a stable prefix
RTC_EPOCH = 1791979200
DATE_PREFIX = "261014 "


def tap(code: int, t: int, gap: int = 500):
    return [f"{t} key {code:#x} down", f"{t + 30} key {code:#x} up"], t + gap


def chord_func_cue(t: int, gap: int = 800):
    """FUNC hold, CUE tap, FUNC release — Digitakt SETTINGS analog on OT."""
    return [
        f"{t} key 0x2d down",
        f"{t + 80} key 0x2a down",
        f"{t + 120} key 0x2a up",
        f"{t + 200} key 0x2d up",
    ], t + gap


def cstr(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("ascii", "replace")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("remix", nargs="?", default=os.environ.get("REMIX"))
    ap.add_argument("--project", default=os.environ.get(
        "OT_PROJECT", str(ROOT / "template_project/!DEF_N1")))
    ap.add_argument("--set-name", default="OCTABAM")
    ap.add_argument("--name", default="PNR")
    a = ap.parse_args()
    remix = registry.remix(a.remix)
    if "RND NAME" not in remix.modules:
        print(f"  [ -- ] verify_rnd_name: {a.remix} carries no RND NAME")
        return 0
    if not EMU.is_file():
        print("  [SKIP] verify_rnd_name: no port binary (make emu-cf)")
        return 0
    pdir = pathlib.Path(a.project).expanduser()
    if not (pdir / "project.work").is_file():
        print(f"  [SKIP] verify_rnd_name: no project at {pdir}")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, REMIX=a.remix, XBUS="1", SPEC="1")
    env.setdefault("BUILD", "0")
    image = OUT / "mainos.bin"
    r = subprocess.run([sys.executable, str(ROOT / "tools/build/build_bus.py")],
                       env=env, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        sys.exit(f"verify_rnd_name: build failed:\n{(r.stdout + r.stderr)[-1500:]}")
    image.write_bytes((ROOT / "out/mainos_bus.bin").read_bytes())

    # Static: FUNC-held keys pointer was rewritten off stock 0x400d0916.
    img = image.read_bytes()
    ptr = struct.unpack_from(">I", img, 0x400D08F2 - 0x40000400)[0]
    if not (0x40A00000 <= ptr < 0x4F000000):
        sys.exit(f"verify_rnd_name: 0x400d08f2 still {ptr:#x}, want DRAM rnd_func_keys")
    print(f"  [PASS] verify_rnd_name: name-editor FUNC keys -> {ptr:#x}")

    card, tree = OUT / "card.img", OUT / "tree"
    r = subprocess.run(
        [str(PY), str(ROOT / "tools/emu/ot_emu/stage_card.py"),
         str(pdir), a.set_name, a.name, "--tree", str(tree), "--out", str(card)],
        cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"verify_rnd_name: stage_card failed:\n{r.stdout[-800:]}{r.stderr[-800:]}")

    lines, tt = [], 2000
    # NO, PROJ, YES, YES, UP, YES -> NAME THE NEW PROJECT (brain pset_new path)
    for code, gap in ((0x32, 400), (0x1c, 1000), (0x31, 1000), (0x31, 1000),
                      (0x33, 600), (0x31, 1400)):
        l, tt = tap(code, tt, gap)
        lines += l
    l, tt = chord_func_cue(tt)
    lines += l
    dump1 = OUT / "name1.bin"
    lines.append(f"{tt} quit")
    script = OUT / "create1.script"
    script.write_text("\n".join(lines) + "\n")
    log = OUT / "create1.txt"
    dumps = (f"{BUF:#x},32={dump1};{CB:#x},4={OUT / 'cb.bin'};"
             f"{WIN:#x},4={OUT / 'win.bin'};{DISP:#x},32={OUT / 'disp.bin'}")
    def run_script(script_path, log_path, mem_dump):
        cmd = [str(EMU), "--image", str(image), "--card", str(card),
               "--set", a.set_name, "--project", a.name, "--load-ms", "90000",
               "--mkii", "--rtc", str(RTC_EPOCH),
               "--live-script", str(script_path), "--mem-dump", mem_dump]
        with open(log_path, "w") as fh:
            return subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)

    r = run_script(script, log, dumps)
    text = log.read_text()
    if r.returncode or "ended on quit" not in text:
        sys.exit(f"verify_rnd_name: create1 run did not finish -- {log}")

    cb = struct.unpack(">I", (OUT / "cb.bin").read_bytes())[0]
    win = struct.unpack(">I", (OUT / "win.bin").read_bytes())[0]
    name = cstr(dump1.read_bytes())
    if cb != CREATE_CB:
        sys.exit(f"verify_rnd_name: editor callback {cb:#x}, want create {CREATE_CB:#x} "
                 f"(name editor not open?) -- {log}")
    if win == 0:
        sys.exit(f"verify_rnd_name: name-editor window handle is 0 -- {log}")
    if not name.startswith(DATE_PREFIX):
        sys.exit(f"verify_rnd_name: buffer {name!r} missing date prefix {DATE_PREFIX!r} -- {log}")
    tail = name[len(DATE_PREFIX):]
    if tail not in POOL:
        sys.exit(f"verify_rnd_name: buffer {name!r} tail {tail!r} not a pool join -- {log}")
    print(f"  [PASS] verify_rnd_name: FUNC+CUE -> {name!r} (create editor open)")

    # Second chord: different name.
    lines, tt = [], 2000
    for code, gap in ((0x32, 400), (0x1c, 1000), (0x31, 1000), (0x31, 1000),
                      (0x33, 600), (0x31, 1400)):
        l, tt = tap(code, tt, gap)
        lines += l
    l, tt = chord_func_cue(tt)
    lines += l
    l, tt = chord_func_cue(tt + 200)
    lines += l
    dump2 = OUT / "name2.bin"
    lines.append(f"{tt} quit")
    script2 = OUT / "create2.script"
    script2.write_text("\n".join(lines) + "\n")
    log2 = OUT / "create2.txt"
    r = run_script(script2, log2, f"{BUF:#x},32={dump2}")
    if r.returncode or "ended on quit" not in log2.read_text():
        sys.exit(f"verify_rnd_name: create2 run did not finish -- {log2}")
    name2 = cstr(dump2.read_bytes())
    if not name2.startswith(DATE_PREFIX) or name2[len(DATE_PREFIX):] not in POOL:
        sys.exit(f"verify_rnd_name: second chord {name2!r} bad -- {log2}")
    if name2 == name:
        print(f"  [PASS] verify_rnd_name: second FUNC+CUE -> {name2!r} (same as first; rare)")
    else:
        print(f"  [PASS] verify_rnd_name: second FUNC+CUE -> {name2!r} (changed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
