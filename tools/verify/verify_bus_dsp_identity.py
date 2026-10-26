#!/usr/bin/env python3
"""Compare supplied bus images at all 24 audio bits and report DSP instructions.

    python3 tools/verify/verify_bus_dsp_identity.py BASE.bin CAND.bin --engine delay
    python3 tools/verify/verify_bus_dsp_identity.py BASE2.bin CAND2.bin --engine delay --grains 2

Build both images separately with the same remix and grain count. This gate
never builds an image or changes a source; generated dumps stay under out/.
--grains records the caller's declared build configuration; it does not infer
the grain count from a binary. Repeat with an independently built two-grain
pair to cover that substitution. --remix supplies the images' module IDs and
knob schema, which must match both images.

The shipping A/B payloads run together, with a SEND feeding each server.
Every instance's raw24 stream (signed int32 containers) must match byte for
byte, including startup and tails. Controls require live engine output,
mode/knob sensitivity and effective automation. Meter values are executed
instructions, NOT hardware cycles; lock-step rendering cannot prove DMA
readback timing, contention or hardware audio quality.
"""
import argparse
import array
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import toolpath  # noqa: E402,F401
import send_probe  # noqa: E402
from remix import registry  # noqa: E402

FRAMES, FS, BLOCKS = 16, 8388607, 8192
DELAY, REVERB = "DELAY SERVER", "REVERB SERVER"
SPECS = ((REVERB, 0), ("SEND", 0), (DELAY, 1), ("SEND", 1))
DELAY_DEFAULTS = dict(DEL=0, REV=0, MODE=0, TIME=40, FDBK=60, TONE=100,
                      PING=64, WET=127, SIZE=1, PTCH=64, SCTR=40, DENS=127)


@dataclass
class Case:
    name: str
    changes: dict = field(default_factory=dict)
    blocks: int = BLOCKS
    split: int = 0
    events: tuple = ()                 # (block, instance index, knob name, value)


def cases(engine):
    result = []
    if engine in ("delay", "all"):
        result += [Case("delay_clean"), Case("delay_tone", {DELAY: {"TONE": 10}}),
                   Case("delay_grain", {DELAY: {"MODE": 1}}),
                   Case("delay_reverse", {DELAY: {"MODE": 2}}),
                   Case("delay_unknown", {DELAY: {"MODE": 7}})]
        for mode in range(3):
            for corner in (0, 127):
                result.append(Case(f"delay_mode{mode}_corner{corner}", {DELAY: dict(
                    MODE=mode, TIME=corner, PING=corner, FDBK=corner, TONE=corner,
                    SIZE=0 if corner == 0 else 3, PTCH=corner)}))
        for size in range(4):
            for j, pitch in enumerate((0, 32, 64, 96, 127)):
                result.append(Case(f"grain_size{size}_pitch{pitch}", {DELAY: dict(
                    MODE=1, SIZE=size, PTCH=pitch, TIME=0 if pitch == 127 else 127,
                    SCTR=(0, 64, 127)[(size + j) % 3], DENS=(127, 64, 0)[j % 3])}))
        for split in (1, 15):
            result.append(Case(f"grain_split{split}", {DELAY: dict(
                MODE=1, SIZE=3, PTCH=0, TIME=0, PING=127, SCTR=127, DENS=32)}, split=split))
        moves = (("MODE", 1), ("PTCH", 127), ("SIZE", 3), ("SCTR", 127),
                 ("DENS", 0), ("DENS", 127), ("SIZE", 2), ("PTCH", 0),
                 ("MODE", 2), ("SIZE", 3), ("TIME", 127), ("MODE", 0),
                 ("TIME", 0), ("FDBK", 127), ("TONE", 0), ("MODE", 1),
                 ("SIZE", 1), ("PTCH", 64), ("WET", 0), ("WET", 127))
        events = tuple((800 + j * 700, 2, knob, value) for j, (knob, value) in enumerate(moves))
        result += [Case("delay_held", blocks=16384),
                   Case("delay_automation", blocks=16384, events=events),
                   Case("delay_automation_split7", blocks=16384, split=7, events=events)]
    if engine in ("reverb", "all"):
        result += [Case(f"reverb_mode{mode}", {REVERB: {"MODE": mode}}) for mode in range(3)]
        result.append(Case("reverb_shimmer", {REVERB: {"SHMR": 127}}))
        moves = (("SHMR", 127), ("SHFT", 0), ("SHFT", 1), ("SHMR", 0),
                 ("SHFT", 2), ("MODE", 2), ("SHMR", 64), ("SHFT", 4),
                 ("SHMR", 0), ("SHFT", 5), ("MODE", 0), ("SHMR", 110), ("SHMR", 0))
        events = tuple((1000 + j * 1000, 0, knob, value) for j, (knob, value) in enumerate(moves))
        result += [Case("reverb_held", blocks=16384),
                   Case("reverb_automation", blocks=16384, events=events),
                   Case("reverb_automation_split7", blocks=16384, split=7, events=events)]
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_audio(path, blocks):
    """Asymmetric, full-precision noise/tones; silence at startup, between bursts and at the end."""
    state, data = 0x1234567, array.array("i")
    assert data.itemsize == 4
    for i in range(blocks * FRAMES):
        state = (1103515245 * state + 12345) & 0x7fffffff
        noise = (((state >> 8) & 65535) - 32768) / 32768
        block = i // FRAMES
        active = 300 <= block < blocks - 2048 and block // 1024 % 4 != 3
        left = .45 * noise + .25 * math.sin(i * .0625) if active else 0
        right = .35 * noise - .2 * math.sin(i * .09375) if active else 0
        data.extend((round(left * FS), round(right * FS)))
    path.write_bytes(data.tobytes())


class Host:
    def __init__(self, image, tag, work, mods, executable, keep_raw):
        self.tag, self.work, self.mods = tag, work, mods
        self.executable, self.keep_raw = executable, keep_raw
        self.mems = [send_probe.dump_mem(image, work / f"{tag}_{p}.mem", p) for p in "AB"]
        self.entries = [send_probe.entry_points(self.mems[core], mods[key].menu.fx2_id)
                        for key, core in SPECS]

    def render(self, case):
        defaults = ({"MODE": 1, "SHMR": 0}, {"REV": 100, "DEL": 0},
                    DELAY_DEFAULTS, {"REV": 0, "DEL": 100})
        parameters = []
        for (key, _), default in zip(SPECS, defaults):
            mod = self.mods[key]
            values = [p.default or 0 for p in mod.params]
            for knob, value in {**default, **case.changes.get(key, {})}.items():
                values[mod.knob_map()[knob]] = value
            parameters.append(values)
        name = f"{self.tag}_{case.name}"
        raw, meter = self.work / f"{name}.raw", self.work / f"{name}.meter"
        source = self.work / f"input_{case.blocks}.raw"
        if not source.exists():
            input_audio(source, case.blocks)
        cmd = [str(self.executable), "-mem", str(self.mems[0]), "-memB", str(self.mems[1]),
               "-init", ",".join(f"{e[0]:x}" for e in self.entries),
               "-proc", ",".join(f"{e[1]:x}" for e in self.entries),
               "-inst", "4", "-core", "0,0,1,1", "-alloc", "1,3,1,3", "-r7", "2,5,2,5",
               "-audioidx", "0,1,2,3", "-audio", "9000", "-inmask", "10",
               "-frames", str(FRAMES), "-blocks", str(case.blocks), "-in", str(source),
               "-stereo", "-out", str(raw), "-meter", str(meter)]
        for values in parameters:
            cmd += ["-params", ",".join(map(str, values))]
        if case.events:
            events = [f"{block}:{inst}:{self.mods[SPECS[inst][0]].knob_map()[knob]}={value}"
                      for block, inst, knob, value in case.events]
            cmd += ["-sched", ",".join(events)]
        if case.split:
            cmd += ["-split", str(case.split)]
        run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        log = run.stdout + run.stderr
        (self.work / f"{name}.log").write_text(log)
        if run.returncode or "HANG" in log:
            raise RuntimeError(f"{name}: dsp_host failed ({run.returncode})\n{log[-2000:]}")
        rows = [list(map(int, line.split())) for line in meter.read_text().splitlines() if line.strip()]
        if len(rows) != case.blocks or any(len(row) != 3 or row[0] != i for i, row in enumerate(rows)):
            raise RuntimeError(f"{name}: incomplete instruction meter")
        steady = rows[512:]
        paths = [raw] + [Path(f"{raw}.i{i}") for i in range(1, 4)]
        audio = [path.read_bytes() for path in paths]
        if any(len(data) != case.blocks * FRAMES * 2 * 4 for data in audio):
            raise RuntimeError(f"{name}: incomplete raw24 output")
        result = dict(hashes=[hashlib.sha256(data).hexdigest() for data in audio],
                      peak=[max(map(abs, array.array("i", data))) for data in audio],
                      instructions_per_sample=[sum(row[c + 1] for row in steady) / len(steady) / FRAMES
                                               for c in range(2)],
                      max_block_instructions=[max(row[c + 1] for row in steady) for c in range(2)])
        if not self.keep_raw:
            for path in paths:
                path.unlink()
        return result, audio


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("baseline", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--engine", choices=("delay", "reverb", "all"), default="all")
    ap.add_argument("--remix", default="bus")
    ap.add_argument("--grains", type=int, choices=(2, 4), default=4)
    ap.add_argument("--host", type=Path, default=send_probe.HOST)
    ap.add_argument("--out", type=Path, help="output directory (default: unique directory under out/)")
    ap.add_argument("--keep-raw", action="store_true", help="retain raw renders as well as logs and meters")
    args = ap.parse_args()
    for name in ("baseline", "candidate", "host"):
        path = getattr(args, name).resolve()
        if not path.is_file():
            ap.error(f"missing {name}: {path}")
        setattr(args, name, path)
    root = ROOT / "out"
    root.mkdir(exist_ok=True)
    work = args.out.resolve() if args.out else Path(tempfile.mkdtemp(prefix="bus-dsp-identity-", dir=root))
    work.mkdir(parents=True, exist_ok=True)
    mods = registry.bound(registry.remix(args.remix))
    report = dict(engine=args.engine, remix=args.remix, declared_grains=args.grains,
                  baseline=dict(path=str(args.baseline), sha256=sha(args.baseline)),
                  candidate=dict(path=str(args.candidate), sha256=sha(args.candidate)),
                  host=dict(path=str(args.host), sha256=sha(args.host)),
                  meter_unit="executed DSP instructions; not hardware cycles", cases=[], controls=[])
    hosts = [Host(image, tag, work, mods, args.host, args.keep_raw)
             for tag, image in (("baseline", args.baseline), ("candidate", args.candidate))]
    saved = {}
    for case in cases(args.engine):
        before, a = hosts[0].render(case)
        after, b = hosts[1].render(case)
        identical = a == b               # Full raw24 byte equality, not a WAV/hash comparison.
        delta = [x - y for x, y in zip(before["instructions_per_sample"], after["instructions_per_sample"])]
        report["cases"].append(dict(name=case.name, blocks=case.blocks, split=case.split,
                                    changes=case.changes, events=case.events, identical=identical,
                                    baseline=before, candidate=after, saved_instructions_per_sample=delta))
        saved[case.name] = before
        print(f"[{'PASS' if identical else 'FAIL'}] {case.name}: raw24 identical={identical}; "
              f"instructions/sample saved A={delta[0]:.3f} B={delta[1]:.3f}", flush=True)
        (work / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    def control(label, condition):
        report["controls"].append(dict(name=label, passed=bool(condition)))
        print(f"[{'PASS' if condition else 'FAIL'}] {label}", flush=True)

    def differs(first, second, stream):
        return saved[first]["hashes"][stream] != saved[second]["hashes"][stream]

    if args.engine in ("delay", "all"):
        control("CLEAN has signal", saved["delay_clean"]["peak"][2] > 0)
        control("TONE is live", differs("delay_clean", "delay_tone", 2))
        control("GRAIN is live", differs("delay_clean", "delay_grain", 2)
                and saved["delay_grain"]["peak"][2] > 0)
        control("REVERSE is live", differs("delay_clean", "delay_reverse", 2)
                and saved["delay_reverse"]["peak"][2] > 0)
        control("unknown MODE falls back to CLEAN", not differs("delay_clean", "delay_unknown", 2))
        control("delay automation changes audio", differs("delay_held", "delay_automation", 2))
    if args.engine in ("reverb", "all"):
        control("reverb has signal", saved["reverb_mode1"]["peak"][0] > 0)
        for mode in (0, 2):
            control(f"reverb MODE {mode} is live", differs(f"reverb_mode{mode}", "reverb_mode1", 0)
                    and saved[f"reverb_mode{mode}"]["peak"][0] > 0)
        control("shimmer is live", differs("reverb_mode1", "reverb_shimmer", 0))
        control("reverb automation changes audio", differs("reverb_held", "reverb_automation", 0))
    ok = all(c["identical"] for c in report["cases"]) and all(c["passed"] for c in report["controls"])
    report["passed"] = ok
    (work / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{'PASS' if ok else 'FAIL'}: {len(report['cases'])} cases; report {work / 'results.json'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
