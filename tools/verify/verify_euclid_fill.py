#!/usr/bin/env python3
"""EUCLID FILL: Euclidean bit patterns + UI contract (fast, no port).

Math matches modules/euclid/control.c. UI checks audit euclid_fill.s so the
popup keeps filter-EUCLID names (STEPS / PULSE / ROT), STEPS locked to
pattern length, encoder A=PULSE / B=ROT / LEVEL=focused, and the key layer.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]

SRC = ROOT / "modules/euclid-fill/euclid_fill.s"

FAILS = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global FAILS
    if ok:
        print(f"  [PASS] {name}" + (f" ({detail})" if detail else ""))
    else:
        FAILS += 1
        print(f"  [FAIL] {name}" + (f": {detail}" if detail else ""))


def eu_pulse(i: int, n: int, k: int) -> bool:
    """Same law as modules/euclid/control.c eu_pulse."""
    return bool(k and (i * k) % n < k)


def pattern(n: int, k: int, rot: int = 0) -> list[int]:
    out = []
    for i in range(n):
        idx = (i + n - (rot % n)) % n
        out.append(1 if eu_pulse(idx, n, k) else 0)
    return out


def _block(src: str, start: str, end: str | None = None) -> str:
    i = src.find(start)
    if i < 0:
        return ""
    j = src.find(end, i + len(start)) if end else len(src)
    if j < 0:
        j = len(src)
    return src[i:j]


def check_ui(src: str) -> None:
    print("UI contract (euclid_fill.s):")

    # Labels — filter EUCLID vocabulary; no ROTATION
    for lab, text in (("L_STEPS", "STEPS"), ("L_PULSES", "PULSE"), ("L_ROT", "ROT")):
        m = re.search(rf"{lab}:\s*\.asciz\s+\"([^\"]*)\"", src)
        check(f"label {lab}", m is not None and m.group(1) == text,
              m.group(1) if m else "missing")
    check("no ROTATION string", "ROTATION" not in src)

    # Window geometry (TEMPO-class compact box)
    for name, val in (("WINW", 92), ("WINH", 54), ("Y_ROW0", 30),
                      ("Y_ROW1", 22), ("Y_ROW2", 14)):
        m = re.search(rf"\.set\s+{name},\s*(\d+)", src)
        check(f"layout {name}={val}", m is not None and int(m.group(1)) == val,
              m.group(1) if m else "missing")

    # Defaults: STEPS seed 16, PULSE 5 (filter EUCLID), ROT 0
    check("default ef_pulses=5",
          re.search(r"ef_pulses:\s*\.long\s+5\b", src) is not None)
    check("default ef_rot=0",
          re.search(r"ef_rot:\s*\.long\s+0\b", src) is not None)
    check("default ef_steps=16",
          re.search(r"ef_steps:\s*\.long\s+16\b", src) is not None)

    # STEPS locked: sync on open / draw / fill / nudge; nudge never targets ef_steps
    for site in ("ef_open", "ef_draw", "ef_fill", "ef_nudge"):
        i = src.find(f"{site}:")
        check(f"{site} calls ef_sync_len",
              i >= 0 and "ef_sync_len" in src[i:i + 800])

    nudge = _block(src, "ef_nudge:", "ef_nudge_rts:")
    check("ef_nudge edits PULSE/ROT only",
          "lea     ef_pulses" in nudge and "lea     ef_rot" in nudge
          and "lea     ef_steps" not in nudge)
    # ef_sync_len clobbers d0-d3; delta must survive on the stack (hw:
    # encoders one-way + L/R dead when parked in d2 alone).
    check("ef_nudge parks delta across ef_sync_len",
          re.search(
              r"movel\s+%d0,-\(%sp\).*?bsr\.w\s+ef_sync_len.*?movel\s+\(%sp\)\+,%d2",
              nudge, re.S) is not None)

    # Cursor is 0=PULSE / 1=ROT (two rows), not three including STEPS
    check("cursor toggles 0<->1 (eoril #1)",
          re.search(r"ef_down:.*?eoril\s+#1", src, re.S) is not None)

    # Key layer: PAGE / YES / NO / UP / DOWN / LEFT / RIGHT
    keys = _block(src, "EF_KEYS:", "EF_ENCS:")
    for code, handler in (
        ("0x1b", "ef_close"),   # PAGE
        ("0x31", "ef_yes"),
        ("0x32", "ef_no"),
        ("0x33", "ef_up"),
        ("0x20", "ef_down"),
        ("0x34", "ef_left"),
        ("0x21", "ef_right"),
    ):
        check(f"key {code} -> {handler}",
              re.search(rf"\.byte\s+{code},.*?\n\s*\.long\s+{handler}\b", keys, re.S)
              is not None)

    # Encoders: A=0 ef_enc, B=1 ef_enc, LEVEL=6 ef_level
    encs = _block(src, "EF_ENCS:", "T_TITLE:")
    check("encoder A (0) -> ef_enc",
          re.search(r"\.byte\s+0,\s*0[^\n]*\n\s*\.long\s+ef_enc\b", encs) is not None)
    check("encoder B (1) -> ef_enc",
          re.search(r"\.byte\s+1,\s*0[^\n]*\n\s*\.long\s+ef_enc\b", encs) is not None)
    check("encoder LEVEL (6) -> ef_level",
          re.search(r"\.byte\s+6,\s*0[^\n]*\n\s*\.long\s+ef_level\b", encs) is not None)
    check("ef_enc focuses cursor from index",
          re.search(r"ef_enc:.*?movel\s+%d1,ef_cursor", src, re.S) is not None)

    # Draw paints all three labels
    draw = _block(src, "ef_draw:", "ef_fill:")
    for lab in ("L_STEPS", "L_PULSES", "L_ROT"):
        check(f"draw uses {lab}", f"lea     {lab}" in draw or f"lea\t{lab}" in draw)

    # Pattern-length sources (NORMAL / PER TRACK)
    sync = _block(src, "ef_sync_len:", "ef_close:")
    check("sync reads PAT_LEN (+0x8e53)", "PAT_LEN" in sync)
    check("sync reads PAT_PER (+0x8e55)", "PAT_PER" in sync)
    check("sync reads TRK_LEN (+0x50)", "TRK_LEN" in sync)


def main() -> int:
    print("Euclidean patterns:")
    check("E(3,8)", pattern(8, 3) == [1, 0, 0, 1, 0, 0, 1, 0])
    check("E(5,16) pulse count", sum(pattern(16, 5)) == 5)
    check("E(4,16) rot 1",
          pattern(16, 4, 1) == pattern(16, 4)[-1:] + pattern(16, 4)[:-1])
    check("E(0,16) empty", pattern(16, 0) == [0] * 16)
    check("E(16,16) full", pattern(16, 16) == [1] * 16)

    remix = sys.argv[1] if len(sys.argv) > 1 else "euclid-fill"
    from remix import registry
    if "EUCLID FILL" not in registry.remix(remix).modules:
        print(f"  [ -- ] verify_euclid_fill: {remix} carries no EUCLID FILL")
        return FAILS

    if not SRC.is_file():
        check("euclid_fill.s present", False, str(SRC))
    else:
        check_ui(SRC.read_text())

    print(f"EUCLID FILL: {FAILS} failed checks")
    return FAILS


if __name__ == "__main__":
    sys.exit(main())
