#!/usr/bin/env python3
"""Supplement audio identity with adversarial input and live DSP state checks.

    python3 tools/verify/verify_bus_dsp_state.py BASE.bin CAND.bin --engine delay --grains 4
    python3 tools/verify/verify_bus_dsp_state.py BASE2.bin CAND2.bin --engine delay --grains 2
    python3 tools/verify/verify_bus_dsp_state.py BASE.bin CAND.bin --engine reverb

Supplied images must use the same module schema and grain count. No builds.
Dirty X startup, full-scale signed/DC/alternating/LSB input and automation
exercise state beyond the normal listening fixture. All four dry inputs are
fed. Every block's complete raw server state ($00..$83), every raw24 output,
and final Y:$00000..$3ffff (262,144 words) must match except repurposed
scratch: delay $4c..$57; reverb $14/$38 only when glided SHMR is exactly zero.
The original delay's L/R control records must also agree and be changing.
These are emulator checks, not proof of hardware DMA timing or all inputs.
"""
import argparse
import array
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import toolpath  # noqa: E402,F401
import image_dsp  # noqa: E402
import send_probe  # noqa: E402
from remix import registry  # noqa: E402
from verify_bus_dsp_identity import DELAY, REVERB, SPECS, DELAY_DEFAULTS, FRAMES, sha  # noqa: E402

BLOCKS, STATE_WORDS = 16384, 0x84


def signal(path):
    data, rng = array.array("i"), 0x1234567
    for i in range(BLOCKS * FRAMES):
        rng = (1103515245 * rng + 12345) & 0x7fffffff
        phase = i // 4096 % 6
        if i < 300 * FRAMES:
            pair = (0, 0)
        elif i >= BLOCKS * FRAMES - 16384:
            pair = (-0x800000, -0x800000)
        elif i >= 3 * BLOCKS * FRAMES // 4 or phase == 0:
            pair = (0x7fffff, 0x7fffff)
        elif phase == 1:
            pair = (-0x800000, -0x800000)
        elif phase == 2:
            pair = (0x7fffff, -0x400000)
        elif phase == 3:
            pair = (0x7fffff if i % 2 else -0x800000, 0)
        elif phase == 4:
            pair = (1 if i % 97 == 0 else 0, -1 if i % 131 == 0 else 0)
        else:
            pair = ((rng & 0xffffff) - 0x800000, ((rng >> 5) & 0x7fffff) - 0x400000)
        data.extend(pair)
    assert data.itemsize == 4
    path.write_bytes(data.tobytes())


def events(engine):
    if engine == "delay":
        moves = (("MODE", 1), ("SIZE", 3), ("PTCH", 127), ("TIME", 127),
                 ("DENS", 0), ("SCTR", 0), ("PTCH", 0), ("SIZE", 2),
                 ("MODE", 2), ("PING", 0), ("MODE", 7), ("SIZE", 0),
                 ("MODE", 1), ("DENS", 127), ("SCTR", 127), ("SIZE", 1),
                 ("TIME", 0), ("PING", 127), ("PTCH", 96), ("MODE", 0),
                 ("SIZE", 3), ("MODE", 1), ("PTCH", 32), ("PTCH", 127), ("PING", 0))
        return [(400 + j * 613, 2, k, v) for j, (k, v) in enumerate(moves)]
    # Change every interval while SHMR is dormant, then re-enable at the
    # smallest nonzero knob before several full-depth on/off transitions.
    return [(400, 0, "SHFT", 0), (1100, 0, "SHFT", 5), (1800, 0, "MODE", 2),
            (2500, 0, "SHFT", 1), (3200, 0, "SHFT", 4), (4000, 0, "SHMR", 1),
            (4800, 0, "SHMR", 0), (5600, 0, "SHFT", 2), (6400, 0, "SHMR", 127),
            (7600, 0, "SHMR", 0), (8500, 0, "MODE", 0), (9400, 0, "SHFT", 3),
            (10300, 0, "SHMR", 1), (11200, 0, "SHMR", 0),
            (12200, 0, "SHMR", 127), (14200, 0, "SHMR", 0)]


def render(image, label, args, mods, work, source):
    mems = [image_dsp.dump_mem(image, work / f"{label}_{p}.mem", p) for p in "AB"]
    original_hashes = [sha(p) for p in mems]
    # Unequal garbage in the two original grain banks must be cleared by
    # the normal warm-up, not accidentally rely on the host's zeroed RAM.
    for path in mems:
        body = path.read_bytes()
        assert body[-9] == 0xff
        dirty = [((i * 0x234567) ^ (0x800000 if i % 2 else 0x5a5a5a)) & 0xffffff
                 for i in range(0x100)]
        dirty[0x82] = 0  # Explicitly request the normal tagged warm-up.
        record = struct.pack("<BII", 1, 0x6200, len(dirty)) + struct.pack("<256I", *dirty)
        path.write_bytes(body[:-9] + record + body[-9:])
    entries = [send_probe.entry_points(mems[c], mods[k].menu.fx2_id) for k, c in SPECS]
    defaults = ({"DEL": 127, "REV": 127, "TIME": 100, "DIFF": 127, "SHMR": 0, "MODE": 1},
                {"DEL": 127, "REV": 127},
                {**DELAY_DEFAULTS, "DEL": 127, "REV": 127, "FDBK": 127, "TONE": 127,
                 "MODE": 1, "TIME": 0, "SCTR": 127},
                {"DEL": 127, "REV": 127})
    params = []
    for (key, _), values in zip(SPECS, defaults):
        mod = mods[key]
        p = [v.default or 0 for v in mod.params]
        for knob, value in values.items():
            p[mod.knob_map()[knob]] = value
        params.append(p)
    target = 2 if args.engine == "delay" else 0
    raw, track, ydump = (work / f"{label}.{ext}" for ext in ("raw", "track", "y"))
    cmd = [str(args.host), "-mem", str(mems[0]), "-memB", str(mems[1]),
           "-init", ",".join(f"{e[0]:x}" for e in entries), "-proc", ",".join(f"{e[1]:x}" for e in entries),
           "-inst", "4", "-core", "0,0,1,1", "-alloc", "1,3,1,3", "-r7", "2,5,2,5",
           "-audioidx", "0,1,2,3", "-audio", "9000", "-inmask", "15", "-frames", str(FRAMES),
           "-blocks", str(BLOCKS), "-in", str(source), "-stereo", "-out", str(raw),
           "-track", ",".join(f"{i:x}" for i in range(STATE_WORDS)), "-trackinst", str(target),
           "-trackout", str(track), "-dumpcore", str(SPECS[target][1]), "-dumpy", f"0,40000,{ydump}",
           "-split", "7,1,15,0"]
    for values in params:
        cmd += ["-params", ",".join(map(str, values))]
    cmd += ["-sched", ",".join(f"{b}:{i}:{mods[SPECS[i][0]].knob_map()[k]}={v}"
                              for b, i, k, v in events(args.engine))]
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (work / f"{label}.log").write_text(run.stdout + run.stderr)
    if run.returncode or "HANG" in run.stdout + run.stderr:
        raise RuntimeError(f"{label}: host failed ({run.returncode})")
    rows = [list(map(int, s.split())) for s in track.read_text().splitlines()]
    assert len(rows) == BLOCKS and all(len(r) == STATE_WORDS + 1 and r[0] == i for i, r in enumerate(rows))
    outputs = [raw] + [Path(f"{raw}.i{i}") for i in range(1, 4)]
    assert all(p.stat().st_size == BLOCKS * FRAMES * 2 * 4 for p in outputs)
    assert ydump.stat().st_size == 0x40000 * 4
    result = dict(command=cmd, parameters=params, extracted_memory_sha256=original_hashes,
                  dirty_memory_sha256=[sha(p) for p in mems], audio_sha256=[sha(p) for p in outputs],
                  state_sha256=sha(track), y_sha256=sha(ydump),
                  live_after_warmup=any(array.array("i", outputs[target].read_bytes())[512*FRAMES*2:]))
    print(f"{label}: captured raw24, all {STATE_WORDS} state words per block and final Y", flush=True)
    return result, rows, outputs, ydump


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("baseline", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--engine", choices=("delay", "reverb"), required=True)
    ap.add_argument("--grains", choices=(2, 4), type=int, default=4)
    ap.add_argument("--remix", default="bus")
    ap.add_argument("--host", type=Path, default=send_probe.HOST)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    for key in ("baseline", "candidate", "host"):
        path = getattr(args, key).resolve()
        if not path.is_file():
            ap.error(f"missing {key}: {path}")
        setattr(args, key, path)
    work = args.out.resolve() if args.out else Path(tempfile.mkdtemp(prefix="bus-state-", dir=ROOT / "out"))
    work.mkdir(parents=True, exist_ok=True)
    source = work / "input.raw"
    signal(source)
    mods = registry.bound(registry.remix(args.remix))
    report = dict(engine=args.engine, declared_grains=args.grains,
                  baseline_image=dict(path=str(args.baseline), sha256=sha(args.baseline)),
                  candidate_image=dict(path=str(args.candidate), sha256=sha(args.candidate)),
                  host=dict(path=str(args.host), sha256=sha(args.host)),
                  input_sha256=sha(source), script_sha256=sha(Path(__file__)), events=events(args.engine))
    before, a, audio_a, y_a = render(args.baseline, "baseline", args, mods, work, source)
    after, b, audio_b, y_b = render(args.candidate, "candidate", args, mods, work, source)
    allowed, unexpected = {}, {}
    for old, new in zip(a, b):
        for off, (x, y) in enumerate(zip(old[1:], new[1:])):
            if x == y:
                continue
            permit = (0x4c <= off < 0x4c + 3 * args.grains if args.engine == "delay" else
                      off in (0x14, 0x38) and old[1+0x0e] == new[1+0x0e] == 0)
            bucket = allowed if permit else unexpected
            bucket.setdefault(f"{off:02x}", dict(blocks=0, first=[old[0], x, y]))["blocks"] += 1
    checks = dict(raw24_identical=all(x.read_bytes() == y.read_bytes() for x, y in zip(audio_a, audio_b)),
                  final_y_identical=y_a.read_bytes() == y_b.read_bytes(),
                  live=before["live_after_warmup"] and after["live_after_warmup"],
                  no_unexpected_state_differences=not unexpected)
    if args.engine == "delay":
        live = [r for r in a[512:] if r[1+0x69] == 0x10000]
        n = args.grains * 3
        records = {tuple(r[1+0x40:1+0x40+n]) for r in live}
        checks.update(original_lr_records_equal=bool(live) and all(r[1+0x40:1+0x40+n] == r[1+0x4c:1+0x4c+n] for r in live),
                      original_records_live=len(records) > 100 and any(any(r) for r in records))
        report["original_grain_record_distinct_states"] = len(records)
        ymem = array.array("I", y_a.read_bytes())
        saturation = {label: {"positive": ymem[start:end].count(0x7fffff),
                              "negative": ymem[start:end].count(0x800000)}
                      for label, start, end in (("line_l", 0x38000, 0x40000),
                                                ("line_r", 0x4000, 0xc000))}
        checks["both_line_stores_saturate_both_signs"] = all(all(v.values()) for v in saturation.values())
        report["final_line_saturation_words"] = saturation
    else:
        gains = [r[1+0x0e] for r in a[512:]]
        checks["shimmer_repeatedly_reaches_exact_zero"] = sum(x != 0 and y == 0 for x, y in zip(gains, gains[1:])) >= 3
        checks["dormant_filter_and_write_phase_live"] = all(len({r[1+off] for r in a[512:4000]}) > 100 for off in (0x0a, 0x0f))
    report.update(baseline=before, candidate=after, checks=checks, allowed_state_differences=allowed,
                  unexpected_state_differences=unexpected, passed=all(checks.values()))
    (work / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {work / 'results.json'}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
