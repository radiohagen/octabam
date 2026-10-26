#!/usr/bin/env python3
"""POST FADER's REV participation bit must never become a held GRAIN note.

    python3 tools/verify/verify_postfader_dsp.py test/send-return-poc --image IMAGE

Runs the supplied image; never builds. Compare tagged and untagged REV words
with the same send coefficient and notes 0/72/84/96. Only the delay's SEND
client receives audio, so changing the host's REV membership cannot change
the delay output. Check the latched note and pitch step as well as all 24
audio bits. This detects a stale negative A2 shifted into the note after
masking A1, including a false held note when no MIDI note has ever arrived.
Repeat with --grains 2 and a separately built two-grain image. This option
records the caller's configuration; it does not infer it from the image.
"""
import argparse
import array
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import toolpath  # noqa: E402,F401
import send_probe  # noqa: E402
import image_dsp  # noqa: E402
from remix import registry  # noqa: E402
from verify_bus_dsp_identity import DELAY, REVERB, DELAY_DEFAULTS, FRAMES, SPECS, input_audio, sha  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BLOCKS = 4096


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("remix")
    ap.add_argument("--image", type=Path, default=ROOT / "out/mainos_bus.bin")
    ap.add_argument("--host", type=Path, default=send_probe.HOST)
    ap.add_argument("--grains", type=int, choices=(2, 4), help="declared image grain count (default: remix)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    remix = registry.remix(args.remix)
    if not {"POST FADER", DELAY, REVERB}.issubset(remix.modules):
        print("[ -- ] held-note DSP gate requires POST FADER and both bus servers")
        return 0
    args.grains = args.grains if args.grains is not None else remix.grains
    for name in ("image", "host"):
        value = getattr(args, name).resolve()
        if not value.is_file():
            ap.error(f"missing {name}: {value}")
        setattr(args, name, value)
    (ROOT / "out").mkdir(exist_ok=True)
    work = args.out.resolve() if args.out else Path(tempfile.mkdtemp(prefix="postfader-dsp-", dir=ROOT / "out"))
    work.mkdir(parents=True, exist_ok=True)
    mods = registry.bound(remix)
    mems = [image_dsp.dump_mem(args.image, work / f"{p}.mem", p) for p in "AB"]
    entries = [send_probe.entry_points(mems[core], mods[key].menu.fx2_id) for key, core in SPECS]
    source = work / "input.raw"
    input_audio(source, BLOCKS)  # Always regenerate; no stale fixture cache.
    report = dict(image=dict(path=str(args.image), sha256=sha(args.image)),
                  host=dict(path=str(args.host), sha256=sha(args.host)),
                  memory_dumps=[dict(path=str(p), sha256=sha(p)) for p in mems],
                  input_sha256=sha(source), script_sha256=sha(Path(__file__)),
                  remix=args.remix, declared_grains=args.grains, cases=[], controls=[])
    audio_by_note = {}
    for note in (0, 72, 84, 96):
        outputs = []
        # PTCH=96 (+12) is intentional: a zero note must keep using that
        # knob; note 84 must override it to unison and note 72 to -12.
        expected_step = {0: 1024, 72: 256, 84: 512, 96: 1024}[note]
        for tag in (0, 0x800000):
            label = f"note{note}_{'tagged' if tag else 'untagged'}"
            raw, track = work / f"{label}.raw", work / f"{label}.track"
            defaults = ({"DEL": 0, "REV": 0, "DLY": 0, "SHMR": 0},
                        {"DEL": 0, "REV": 0},
                        {**DELAY_DEFAULTS, "MODE": 1, "REV": 100, "PTCH": 96},
                        {"DEL": 100, "REV": 0})
            parameters = []
            for (key, _), default in zip(SPECS, defaults):
                mod = mods[key]
                values = [p.default or 0 for p in mod.params]
                for knob, value in default.items():
                    values[mod.knob_map()[knob]] = value
                parameters.append(values)
            cmd = [str(args.host), "-mem", str(mems[0]), "-memB", str(mems[1]),
                   "-init", ",".join(f"{e[0]:x}" for e in entries),
                   "-proc", ",".join(f"{e[1]:x}" for e in entries),
                   "-inst", "4", "-core", "0,0,1,1", "-alloc", "1,3,1,3", "-r7", "2,5,2,5",
                   "-audioidx", "0,1,2,3", "-audio", "9000", "-inmask", "8",
                   "-frames", str(FRAMES), "-blocks", str(BLOCKS), "-in", str(source),
                   "-stereo", "-out", str(raw), "-track", "6a,3e", "-trackinst", "2", "-trackout", str(track),
                   "-pword", f"2:1={tag | (100 << 16) | (note << 8):x},3:0=e40000"]
            for values in parameters:
                cmd += ["-params", ",".join(map(str, values))]
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            log = run.stdout + run.stderr
            (work / f"{label}.log").write_text(log)
            if run.returncode or "HANG" in log:
                raise RuntimeError(f"{label}: dsp_host failed ({run.returncode})\n{log[-2000:]}")
            rows = [list(map(int, line.split())) for line in track.read_text().splitlines() if line.strip()]
            states_ok = (len(rows) == BLOCKS and all(len(row) == 3 and row[0] == i for i, row in enumerate(rows))
                         and all(row[1:] == [note, expected_step] for row in rows[512:]))
            output = Path(f"{raw}.i2").read_bytes()
            complete = len(output) == BLOCKS * FRAMES * 2 * 4
            live = complete and any(array.array("i", output))
            report["cases"].append(dict(name=label, note=note, rev_word=tag | (100 << 16) | (note << 8),
                                        expected_step=expected_step, states_ok=states_ok, live=live,
                                        audio_sha256=sha(Path(f"{raw}.i2")), command=cmd))
            print(f"[{'PASS' if states_ok and live else 'FAIL'}] {label}: note/pitch state={states_ok}, live raw24={live}", flush=True)
            outputs.append(output)
        identical = outputs[0] == outputs[1]
        report["controls"].append(dict(name=f"note{note}: tag leaves delay audio unchanged", passed=identical))
        audio_by_note[note] = outputs[1]
    for label, condition in (
            ("note 72 and 84 produce different pitches", audio_by_note[72] != audio_by_note[84]),
            ("note 84 overrides PTCH=96", audio_by_note[84] != audio_by_note[0]),
            ("no note keeps PTCH=96", audio_by_note[0] == audio_by_note[96])):
        report["controls"].append(dict(name=label, passed=condition))
    for control in report["controls"]:
        print(f"[{'PASS' if control['passed'] else 'FAIL'}] {control['name']}")
    report["passed"] = all(c["states_ok"] and c["live"] for c in report["cases"]) and all(c["passed"] for c in report["controls"])
    (work / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{'PASS' if report['passed'] else 'FAIL'}: report {work / 'results.json'}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
