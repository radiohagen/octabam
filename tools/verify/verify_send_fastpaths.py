#!/usr/bin/env python3
"""Compare isolated SEND ramp/sample bodies, including tagged transitions.

    python3 tools/verify/verify_send_fastpaths.py BEFORE.asm AFTER.asm --image BUILT.bin

The supplied image provides only the stock frame setup. This gate assembles
each supplied source's init and cnt_done body into a private test program;
it does not build firmware or qualify registration, rotation, housekeeping,
cross-core scheduling, the ColdFire hook, or hardware DMA timing. The full
bus and firmware gates cover those protocols separately.

Compare 24 cases at every block boundary: all 132 X-state words, 32 bus
accumulator snapshots, address/modulo/offset registers and y0. Compare raw24
audio and the final 512 seeded Y words too. The POST FADER wrapper sets bit23
before every call, including scheduled gain changes, and captures the raw
words so the participation tags are checked rather than assumed.
"""
import argparse
import array
import hashlib
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
from remix import bus_source, registry  # noqa: E402

BLOCKS, FRAMES, STATE_WORDS = 512, 16, 0x84
REGISTERS = [f"{kind}{i}" for kind in ("r", "m", "n") for i in range(8)] + ["y0"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(space, address, words):
    return struct.pack("<BII", space, address, len(words)) + struct.pack(f"<{len(words)}I", *words)


def signal(path):
    data, rng = array.array("i"), 0x1234567
    assert data.itemsize == 4
    corners = ((0x7fffff, 0x7fffff), (-0x800000, -0x800000), (0x7fffff, -0x800000),
               (1, -1), (-1, -1), (0, 1), (0, 0), (0x7fffff, 0x7ffffe))
    for i in range(BLOCKS * FRAMES):
        rng = (1103515245 * rng + 12345) & 0x7fffffff
        data.extend(corners[i % len(corners)] if i % 3 else
                    ((rng & 0xffffff) - 0x800000, ((rng >> 3) & 0xffffff) - 0x800000))
    path.write_bytes(data.tobytes())


def wrapper(source, tagged):
    if tagged:
        source = bus_source.transform("SEND", source, registry.remix("test/send-return-poc"))
    # Transform the entire source first: the original participation-count
    # anchors remain checked even though execution starts after registration.
    init = source[source.index("init:"):source.index("proc:")]
    body = source[source.index("cnt_done:"):]
    code = init + """
entry:
        move #>$1000,r2
        move #>$1100,r4
        move #>$ffffff,m2
        move #>$ffffff,m4
"""
    for offset in range(2):
        code += f"        move x:(r6+${offset:x}),a\n"
        if tagged:
            code += "        or #>$800000,a\n"
        code += ("        move a1,x0\n"
                 f"        move x0,x:(r6+${offset:x})\n"
                 f"        move x0,x:(r7+${0x60+offset:x})\n")
    code += "        bsr cnt_done\n"
    for i, reg in enumerate(REGISTERS):
        code += f"        move {reg},a\n        move a,x:(r7+${0x20+i:x})\n"
    for i in range(FRAMES):
        for ybase, xbase in ((0x1000, 0x40), (0x1100, 0x50)):
            code += f"        move y:>${ybase+i:x},a\n        move a,x:(r7+${xbase+i:x})\n"
    return code + "        rts\n" + body


def cases(tagged):
    result = [(name, [delay, reverb], 0, (), False)
              for name, delay, reverb in (("zero", 0, 0), ("both", 127, 127),
                                          ("del", 127, 0), ("rev", 0, 127))]
    result += [("boundary_fraction", [0, 0], 0, (0x100, 0x7fff00), False),
               ("nearzero", [0, 0], 0, (0x100, 0x200), False),
               ("asymmetric", [0, 0], 0, (0x123400, 0x345600), False)]
    result += [(f"changes_split{split}", [127, 0], split, (), True) for split in (0, 1, 7, 15)]
    if tagged:
        result += [("muted_participant", [0, 0], 0, (0x800000, 0x800000), False),
                   ("boundary_tag", [0, 0], 7, (0x800100, 0xffff00), False)]
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("baseline", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--image", type=Path, required=True, help="image supplying the frame setup; no build")
    ap.add_argument("--host", type=Path, default=send_probe.HOST)
    ap.add_argument("--assembler", type=Path, default=ROOT / "vendor/dsp56300/build/source/dsp_host/dsp_asm")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    for key in ("baseline", "candidate", "image", "host", "assembler"):
        path = getattr(args, key).resolve()
        if not path.is_file():
            ap.error(f"missing {key}: {path}")
        setattr(args, key, path)
    work = args.out.resolve() if args.out else Path(tempfile.mkdtemp(prefix="send-fastpaths-", dir=ROOT / "out"))
    work.mkdir(parents=True, exist_ok=True)
    if any(work.iterdir()):
        ap.error(f"output directory must be empty: {work}")
    source = work / "input.raw"
    signal(source)
    template = image_dsp.dump_mem(args.image, work / "template.mem", "A").read_bytes()
    assert template[-9:] == struct.pack("<BII", 255, 0, 0)
    seeds = [(0x7fffff, 0x800000, 0, 1, 0xffffff, 0x123456, 0xfedcba)[i % 7] for i in range(0x200)]
    report = dict(script_sha256=sha(Path(__file__)),
                  image=dict(path=str(args.image), sha256=sha(args.image)),
                  template_sha256=sha(work / "template.mem"),
                  host=dict(path=str(args.host), sha256=sha(args.host)),
                  assembler=dict(path=str(args.assembler), sha256=sha(args.assembler)),
                  transformer_sha256=sha(ROOT / "modules/post-fader/engine.py"),
                  input_sha256=sha(source), blocks=BLOCKS, frames_per_block=FRAMES,
                  register_snapshots=REGISTERS, sources={}, programs=[], cases=[], passed=False,
                  scope="Isolated SEND init/ramp/sample body; no bus protocol, ColdFire or hardware proof.")
    sources = {}
    for label in ("baseline", "candidate"):
        path = getattr(args, label)
        sources[label] = path.read_text()
        (work / f"{label}.asm").write_text(sources[label])
        report["sources"][label] = dict(path=str(path), sha256=sha(path))
    receipt = work / "results.json"
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    for tagged in (False, True):
        programs = {}
        for label, text in sources.items():
            prefix = work / f"micro-{int(tagged)}-{label}"
            prefix.with_suffix(".asm").write_text(wrapper(text, tagged))
            command = [str(args.assembler), "-in", str(prefix.with_suffix(".asm")), "-org", "10000",
                       "-out", str(prefix.with_suffix(".bin")), "-sym", str(prefix.with_suffix(".sym"))]
            run = subprocess.run(command, check=True, capture_output=True, text=True)
            prefix.with_suffix(".log").write_text(run.stdout + run.stderr)
            symbols = {key: int(value, 16) for key, value in
                       (line.split() for line in prefix.with_suffix(".sym").read_text().splitlines() if line.strip())}
            code = prefix.with_suffix(".bin").read_bytes()
            words = [int.from_bytes(code[i:i+3], "little") for i in range(0, len(code), 3)]
            memory = prefix.with_suffix(".mem")
            memory.write_bytes(template[:-9] + record(0, 0x10000, words) + record(2, 0x1000, seeds) + template[-9:])
            programs[label] = (memory, symbols)
            report["programs"].append(dict(tagged=tagged, label=label, command=command,
                                          source_sha256=sha(prefix.with_suffix(".asm")), memory_sha256=sha(memory)))
        for name, params, split, pwords, automate in cases(tagged):
            runs = {}
            for label, (memory, symbols) in programs.items():
                prefix = work / f"run-{int(tagged)}-{name}-{label}"
                command = [str(args.host), "-mem", str(memory), "-init", f"{symbols['init']:x}",
                           "-proc", f"{symbols['entry']:x}", "-inst", "1", "-r7", "2", "-alloc", "1",
                           "-audio", "9000", "-inmask", "1", "-in", str(source), "-stereo", "-frames", str(FRAMES),
                           "-blocks", str(BLOCKS), "-params", ",".join(map(str, params + [0] * 10)),
                           "-out", str(prefix.with_suffix(".raw")), "-meter", str(prefix.with_suffix(".meter")),
                           "-track", ",".join(f"{i:x}" for i in range(STATE_WORDS)), "-trackinst", "0",
                           "-trackout", str(prefix.with_suffix(".track")), "-dumpcore", "0",
                           "-dumpy", f"1000,1200,{prefix.with_suffix('.y')}", "-split", str(split)]
                if pwords:
                    command += ["-pword", ",".join(f"0:{i:x}={value:x}" for i, value in enumerate(pwords))]
                if automate:
                    command += ["-sched", "8:0:0=0,8:0:1=127,96:0:0=0,96:0:1=0,192:0:0=100,192:0:1=64,"
                                          "288:0:0=1,288:0:1=0,384:0:0=0,384:0:1=0"]
                run = subprocess.run(command, capture_output=True, text=True)
                prefix.with_suffix(".log").write_text(run.stdout + run.stderr)
                if run.returncode or "HANG" in run.stdout + run.stderr:
                    raise RuntimeError(f"{prefix}: host failed ({run.returncode})")
                rows = [list(map(int, line.split())) for line in prefix.with_suffix(".track").read_text().splitlines()]
                meter = [list(map(int, line.split())) for line in prefix.with_suffix(".meter").read_text().splitlines()]
                assert len(rows) == BLOCKS and all(len(r) == STATE_WORDS + 1 and r[0] == i for i, r in enumerate(rows))
                assert len(meter) == BLOCKS and all(len(r) == 2 and r[0] == i for i, r in enumerate(meter))
                assert prefix.with_suffix(".raw").stat().st_size == BLOCKS * FRAMES * 2 * 4
                assert prefix.with_suffix(".y").stat().st_size == 0x200 * 4
                assert all(bool(r[1+offset] & 0x800000) == tagged for r in rows for offset in (0x60, 0x61))
                if automate:
                    assert all(len({r[1+offset] & 0x7fff00 for r in rows}) >= 3 for offset in (0x60, 0x61))
                runs[label] = dict(command=command, raw_sha256=sha(prefix.with_suffix(".raw")),
                                   state_sha256=sha(prefix.with_suffix(".track")), y_sha256=sha(prefix.with_suffix(".y")),
                                   meter_sha256=sha(prefix.with_suffix(".meter")), instructions=sum(r[1] for r in meter),
                                   raw_tag_bits_checked=True)
            for key in ("raw_sha256", "state_sha256", "y_sha256"):
                assert runs["baseline"][key] == runs["candidate"][key], (tagged, name, key)
            report["cases"].append(dict(tagged=tagged, name=name, split=split, raw_words=pwords,
                                        scheduled=automate, runs=runs, identical=True))
            receipt.write_text(json.dumps(report, indent=2) + "\n")
            print(f"PASS tagged={tagged} {name}: raw24, full state, bus words and ABI snapshots exact", flush=True)
    report["passed"] = True
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {len(report['cases'])} isolated pairs; {receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
