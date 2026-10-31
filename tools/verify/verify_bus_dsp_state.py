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
With --derived-delay-mask, new delay scratch $6e/$6f/$7e must satisfy its
step-mask and TIME-cache invariants rather than simply being ignored.
The original delay's L/R control records must also agree and be changing.
Use --exact-state when both images already contain the same optimizations:
it forbids every scratch exception and replaces the old L/R cache-duplication
requirement with complete state equality (the shared cache still must evolve).
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
SPLITS = (7, 1, 15, 0)


def delay_cache_invariants(rows, calls_per_block):
    """Check derived scratch only after the delay has actually processed.

    delay_server.asm's dwarmtag/dwarmrun accepts tag $2e0000, clears one
    chunk per proc call, and processes only when the entry count is >=256.
    A final row at count 256 may therefore still be the last warm-up call.
    Account for both calls of a split block: entry count 255 with two calls
    warms once and then processes. Controls do not change between those
    calls in this fixture, so the final steps also describe the first call.
    None marks a wholly warming block; it grants no scratch exception.
    """
    if calls_per_block not in (1, 2):
        raise ValueError("the dispatcher makes one or two calls per block")
    result = []
    for index, row in enumerate(rows):
        previous = rows[index - 1] if index else None
        # render() explicitly dirties raw $82 to zero before init. An
        # unrecognised tag starts at count zero on that call.
        warm = previous[1+0x82] if previous is not None else 0
        count = warm & 0x1ff if warm & 0xfffe00 == 0x2e0000 else 0
        if count + calls_per_block <= 0x100:
            result.append(None)
            continue
        mask = row[1+0x36] | row[1+0x37] | row[1+0x2f] | row[1+0x64]
        q8 = row[1+0x26]
        if q8 & 0x800000:
            q8 -= 1 << 24
        q8 = min(max(q8, 0x800), 0x7ff800)
        result.append({
            0x6e: row[1+0x6e] == mask,
            0x6f: row[1+0x6f] == (q8 >> 8 if mask == 0 else previous[1+0x6f]),
            0x7e: row[1+0x7e] == ((q8 & 255) << 15 if mask == 0 else previous[1+0x7e]),
        })
    return result


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
           "-split", ",".join(map(str, SPLITS))]
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
    ap.add_argument("--exact-state", action="store_true",
                    help="compare optimized images with no scratch-state exceptions")
    ap.add_argument("--host", type=Path, default=send_probe.HOST)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--derived-delay-mask", action="store_true",
                    help="check the candidate step mask and settled TIME caches at $6e/$6f/$7e")
    args = ap.parse_args()
    if args.derived_delay_mask and args.engine != "delay":
        ap.error("--derived-delay-mask requires --engine delay")
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
    # Exceptions and unconditional checks share one oracle. In particular,
    # a corrupt value equal to the baseline's old scratch is still checked.
    derived = (delay_cache_invariants(b, 2 if 0 < SPLITS[2] < FRAMES else 1)
               if args.derived_delay_mask else [None] * len(b))
    for index, (old, new) in enumerate(zip(a, b)):
        for off, (x, y) in enumerate(zip(old[1:], new[1:])):
            if x == y:
                continue
            permit = not args.exact_state and (
                0x4c <= off < 0x4c + 3 * args.grains if args.engine == "delay" else
                off in (0x14, 0x38) and old[1+0x0e] == new[1+0x0e] == 0)
            if args.derived_delay_mask and off in (0x6e, 0x6f, 0x7e):
                permit = not args.exact_state and derived[index] is not None and derived[index][off]
            bucket = allowed if permit else unexpected
            bucket.setdefault(f"{off:02x}", dict(blocks=0, first=[old[0], x, y]))["blocks"] += 1
    checks = dict(raw24_identical=all(x.read_bytes() == y.read_bytes() for x, y in zip(audio_a, audio_b)),
                  final_y_identical=y_a.read_bytes() == y_b.read_bytes(),
                  live=before["live_after_warmup"] and after["live_after_warmup"],
                  no_unexpected_state_differences=not unexpected)
    report["exact_state_required"] = args.exact_state
    if args.exact_state:
        checks["all_state_identical"] = a == b
    if args.engine == "delay":
        if args.derived_delay_mask:
            live_derived = [(row, check) for row, check in zip(b, derived) if check is not None]
            masks = [row[1+0x6e] for row, _ in live_derived]
            checks["derived_mask_matches_steps"] = bool(live_derived) and all(check[0x6e] for _, check in live_derived)
            checks["derived_time_caches_match_or_hold"] = bool(live_derived) and all(check[0x6f] and check[0x7e] for _, check in live_derived)
            report["derived_first_live_block"] = live_derived[0][0][0] if live_derived else None
            report["derived_live_blocks_checked"] = len(live_derived)
            report["settled_fraction_values"] = sorted({row[1+0x7e] for row, _ in live_derived if row[1+0x6e] == 0})
            checks["derived_mask_zero_and_active"] = {v == 0 for v in masks} == {False, True}
        live = [r for r in a[512:] if r[1+0x69] == 0x10000]
        n = args.grains * 3
        records = {tuple(r[1+0x40:1+0x40+n]) for r in live}
        checks["original_records_live"] = len(records) > 100 and any(any(r) for r in records)
        if not args.exact_state:
            checks["original_lr_records_equal"] = bool(live) and all(
                r[1+0x40:1+0x40+n] == r[1+0x4c:1+0x4c+n] for r in live)
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
