#!/usr/bin/env python3
"""Prepare owned integration fixtures; never edit the source project.

Usage: .venv/bin/python3 tools/verify/prepare_mattias_fixture.py SOURCE OUTPUT
OUTPUT must not exist. See docs/guide/FORK_WORKFLOW.md for the release gates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/harness"))
import ab_fixture

otp = ab_fixture.otp


def hashes(source):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(source.iterdir()) if p.is_file()}


def prepare(source, output):
    source = source.resolve()
    output = output.resolve()
    if output == source or source in output.parents or output in source.parents:
        raise ValueError("source and output must be separate, non-nested directories")
    for name in ["project.work", *(f"bank{i:02d}.work" for i in range(1, 17))]:
        if not (source / name).is_file():
            raise ValueError(f"source lacks {name}")
    before = hashes(source)
    output.mkdir(parents=True, exist_ok=False)
    base = ab_fixture.prepare(source, output / "base")
    for bank in sorted(base.glob("bank*.work")):
        def level(data):
            for part in range(8):
                off = otp.PART_BASE + part * otp.PART_STRIDE
                for track in range(8):
                    data[off + 0x1b + track * 2] = 64
        otp._bank_write(base, int(bank.stem[4:]), level, guard=False)

    hosted = output / "hosted"
    shutil.copytree(base, hosted)
    otp.host_rig(hosted, "mattias-bottleservice", guard=False)
    otp.thru_track(hosted, 1, guard=False)

    scenes = output / "midi-scenes"
    shutil.copytree(base, scenes)
    for bank in sorted(scenes.glob("bank*.work")):
        def normalize(data):
            for part in range(8):
                off = otp.PART_BASE + part * otp.PART_STRIDE
                for track in range(8):
                    for start in (otp.P1_OFF + track * 24, otp.P2_OFF + track * 30):
                        data[off + start:off + start + 12] = bytes(12)
            patterns = [m.start() for m in re.finditer(b"PTRN", data)] + [otp.PART_BASE]
            if len(patterns) != 17:
                raise ValueError("expected sixteen native pattern records")
            data[patterns[2] - 5] = 1  # the upstream sw scenario needs pattern 2 -> Part 2
        otp._bank_write(scenes, int(bank.stem[4:]), normalize, guard=False)

    if hashes(source) != before:
        raise RuntimeError("source project changed during fixture preparation")
    for directory in (base, hosted, scenes):
        for path in directory.glob("bank*.*"):
            if path.suffix not in (".work", ".strd"):
                continue
            data = path.read_bytes()
            if int.from_bytes(data[-2:], "big") != sum(data[0x10:-2]) & 0xffff:
                raise ValueError(f"bad bank checksum: {path}")
    receipt = dict(source=str(source), source_hashes=before, source_unchanged=True,
                   fixtures={p.name: hashes(p) for p in (base, hosted, scenes)})
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    prepare(args.source, args.output)
    print(f"Prepared base, hosted and midi-scenes fixtures in {args.output}")


if __name__ == "__main__":
    main()
