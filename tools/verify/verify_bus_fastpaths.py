#!/usr/bin/env python3
"""Qualify bus fast paths against a frozen image, including their transitions.

    python3 tools/verify/verify_bus_fastpaths.py BEFORE.bin AFTER.bin
    python3 tools/verify/verify_bus_fastpaths.py OLD_ROUTED.bin NEW_ROUTED.bin --post-fader

Both images must have the same routing and grain configuration. No builds.
Compare all four raw24 streams, the selected instance's complete r7 block at
every block boundary, and all 262,144 words of the selected core's final Y
data, without exclusions. dsp_host keeps P separate from Y in the shared
address range; this Y capture does not prove program-memory immutability.
The full firmware gates exercise the installed module separately.
Constant raw tagged fractional SEND
controls supplement the separate real firmware mute/LEVEL tests; they do not
simulate the ColdFire hook or live RETURNS. The host cannot schedule raw
-pword values: tagged gain transitions need the separate isolated SEND and
real firmware gates.
Instruction totals are emulator work, not hardware cycles or DMA acceptance.
"""
import argparse
import array
import json
from pathlib import Path
import tempfile

from verify_bus_dsp_identity import (Case, Host, REVERB, ROOT, SPECS, FRAMES,
                                     registry, send_probe, sha)


def compare_y_data(before, after):
    """Compare every captured Y word, including addresses also used in P.

    dsp_host constructs Memory with its P/XY bridge at $200000, above this
    capture, and shares only X/Y between cores. Window P uploads are copied
    into each core by image_dsp; they are not Y initial values. Consequently
    a difference anywhere in this Y dump is a real data difference.
    """
    if len(before) != 0x40000 * 4 or len(after) != 0x40000 * 4:
        raise RuntimeError("incomplete Y capture")
    return dict(final_y_data_identical=before == after)


def reverb_weights(state, ydata):
    words, base = array.array("I", ydata), state[-1][1+0x0d]
    if not 0 <= base <= len(words) - 16:
        raise RuntimeError(f"invalid reverb injection table address {base:x}")
    return [words[base + 2 * line] for line in range(8)]


def cases(tagged):
    """(case, captured instance, raw SEND words); conditions are checked below."""
    rows = []
    for mode in range(3):
        for shimmer in (0, 127):
            rows.append((Case(f"verb_m{mode}_shmr{shimmer}",
                              {REVERB: dict(MODE=mode, SHMR=shimmer)}), 0, ()))
    for tone in (64, 127):
        for gate in (0, 8):
            rows.append((Case(f"verb_cost_tone{tone}_gate{gate}",
                              {REVERB: dict(MODE=1, SHMR=0, TONE=tone, GATE=gate)}), 0, ()))
    # Drive the LO filter before freezing its nonzero history at coefficient
    # zero. Gate transitions share this history; all controls get long holds.
    changes = ((600, "TONE", 127), (1500, "GATE", 20), (2000, "TONE", 64),
               (2600, "GATE", 0), (3000, "TONE", 65), (3400, "DIFF", 0),
               (3800, "TONE", 0), (4200, "SHMR", 127), (4600, "MODE", 2),
               (5000, "SHMR", 0), (5300, "GATE", 8), (5600, "DIFF", 127),
               (6200, "MODE", 0), (6500, "TIME", 127), (6800, "SIZE", 0),
               (7000, "GATE", 0), (7200, "SIZE", 127))
    events = tuple((block, 0, knob, value) for block, knob, value in changes)
    for split in (0, 1, 7, 15):
        # DLY=0 removes the delay repeats from the gate detector. Direct REV
        # sends still excite the tank, then its final input silence lets the
        # enabled gate close before the block-7000 disable/reset.
        rows.append((Case(f"verb_transitions_s{split}", {REVERB: {"DLY": 0}},
                          events=events, split=split), 0, ()))
    for delay, reverb in ((0, 0), (100, 0), (0, 100), (100, 83), (1, 1), (127, 127)):
        for split in (0, 7):
            rows.append((Case(f"send_d{delay}_r{reverb}_s{split}",
                              {"SEND": dict(DEL=delay, REV=reverb)},
                              blocks=4096, split=split), 1 if split == 0 else 3, ()))
    if not tagged:
        moves = ((600, 127, 0), (1000, 127, 127), (1400, 0, 127), (1800, 0, 0),
                 (2300, 1, 1), (2600, 100, 83), (2900, 99, 82), (3200, 0, 0),
                 (3700, 127, 127), (4300, 0, 0), (5000, 83, 100), (5700, 0, 0))
        events = tuple((block, instance, knob, value)
                       for block, delay, reverb in moves for instance in (1, 3)
                       for knob, value in (("DEL", delay), ("REV", reverb)))
        for split in (0, 1, 7, 15):
            rows.append((Case(f"send_transitions_s{split}", {"SEND": dict(DEL=0, REV=0)},
                              events=events, split=split), 1 if split < 2 else 3, ()))
    else:
        # Original membership stays set even at zero scaled gain. Include the
        # smallest published fraction and fractional nonzero gains. The last
        # pair deliberately exceeds the publisher's maximum 0xff0000 and
        # includes a malformed low byte, to challenge the decoder masks.
        for delay, reverb in ((0x800000, 0x800000), (0x800100, 0x800000),
                              (0x800000, 0x800100), (0x800100, 0x800100),
                              (0xa0ab00, 0xc0cd00), (0xff7f00, 0xffffff)):
            for split in (0, 7):
                words = tuple((inst, off, value) for inst in (1, 3)
                              for off, value in ((0, delay), (1, reverb)))
                kind = "boundary_words" if (delay, reverb) == (0xff7f00, 0xffffff) else "words"
                rows.append((Case(f"send_{kind}_{delay:x}_{reverb:x}_s{split}",
                                  blocks=4096, split=split), 1 if split == 0 else 3, words))
    return rows


def capture(host, case, target, words):
    label = f"{host.tag}_{case.name}"
    state, ydump = (host.work / f"{label}.{ext}" for ext in ("track", "y"))
    extra = ["-track", ",".join(f"{i:x}" for i in range(0x84)),
             "-trackinst", str(target), "-trackout", str(state),
             "-dumpcore", str(SPECS[target][1]), "-dumpy", f"0,40000,{ydump}"]
    if words:
        extra += ["-pword", ",".join(f"{i}:{off:x}={value:x}" for i, off, value in words)]
    result, audio = host.render(case, extra_args=extra)
    rows = [list(map(int, line.split())) for line in state.read_text().splitlines()]
    if len(rows) != case.blocks or any(len(row) != 0x85 or row[0] != i
                                     for i, row in enumerate(rows)):
        raise RuntimeError(f"{label}: incomplete state capture")
    if ydump.stat().st_size != 0x40000 * 4:
        raise RuntimeError(f"{label}: incomplete Y capture")
    result.update(state_sha256=sha(state), y_sha256=sha(ydump), raw_words=words)
    return result, audio, rows, ydump.read_bytes()


def transition_controls(name, state, ydata):
    """Require the intended branch transitions, not merely a startup zero."""
    value = lambda block, offset: state[block][1 + offset]
    if name.startswith("verb_cost"):
        flat, ungated = "tone64_" in name, name.endswith("_gate0")
        checks = dict(lo_branch_selected=all((r[1+0x36] == 0) == flat for r in state[512:]),
                      gate_branch_selected=all(r[1+0x29] == (0x400000 if ungated else 0x1000)
                                               for r in state[512:]),
                      shimmer_zero=all(r[1+0x0e] == 0 for r in state[512:]))
        return dict(name=name, checks=checks, passed=all(checks.values()))
    if name.startswith("verb_transitions"):
        table = value(-1, 0x0b)
        words = array.array("I", ydata)
        if not 0 <= table <= len(words) - 40:
            raise RuntimeError(f"{name}: invalid LO state table address {table:x}")
        history = [words[table + 5 * line + 4] for line in range(8)]
        checks = dict(
            lo_active_then_glides_to_zero=(value(1999, 0x36) > value(2000, 0x36) > 0
                and all(r[1+0x36] == 0 for r in state[2400:2600])),
            lo_reenabled_then_frozen=(value(3300, 0x36) > value(3800, 0x36) > 0
                and all(r[1+0x36] == 0 for r in state[4200:])),
            frozen_lo_history_nonzero=all(history),
            gate_active_then_disabled=(value(2599, 0x29) == 0x1c00
                and value(2600, 0x29) == 0x400000
                and value(6999, 0x29) == 0x1000
                and value(7000, 0x29) == 0x400000),
            gate_closed_before_disable=value(6999, 0x27) < 0x400000,
            gate_full_after_disable=all(r[1+0x27] == 0x7fffff for r in state[7000:]),
            shimmer_active_then_glides_to_zero=(value(4999, 0x0e) > value(5000, 0x0e) > 0
                and all(r[1+0x0e] == 0 for r in state[5300:])))
        return dict(name=name, checks=checks, final_lo_table=table,
                    final_lo_history=history, passed=all(checks.values()))
    if name.startswith("send_transitions"):
        checks = {}
        for gain, step in ((0x15, 0x16), (0x17, 0x18)):
            checks[f"gain_{gain:x}_falls_then_reaches_zero"] = (
                value(3199, gain) > value(3200, gain) > 0
                and bool(value(3200, step) & 0x800000)
                and all(r[1+gain] == r[1+step] == 0 for r in state[3400:3700]))
            checks[f"gain_{gain:x}_reenabled_then_fades_to_zero"] = (
                value(5699, gain) > value(5700, gain) > 0
                and bool(value(5700, step) & 0x800000)
                and all(r[1+gain] == r[1+step] == 0 for r in state[6000:]))
            checks[f"step_{step:x}_positive_negative_settled"] = {
                0 if r[1+step] == 0 else -1 if r[1+step] & 0x800000 else 1
                for r in state[512:]} == {-1, 0, 1}
        return dict(name=name, checks=checks, passed=all(checks.values()))
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("baseline", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--post-fader", action="store_true")
    ap.add_argument("--remix", help="defaults to bus or send-return-poc with --post-fader")
    ap.add_argument("--host", type=Path, default=send_probe.HOST)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--only", help="substring selection for focused diagnosis")
    args = ap.parse_args()
    for name in ("baseline", "candidate", "host"):
        path = getattr(args, name).resolve()
        if not path.is_file():
            ap.error(f"missing {name}: {path}")
        setattr(args, name, path)
    work = args.out.resolve() if args.out else Path(tempfile.mkdtemp(prefix="bus-fastpaths-", dir=ROOT / "out"))
    work.mkdir(parents=True, exist_ok=True)
    receipt = work / "results.json"
    if receipt.exists():
        ap.error(f"refusing to overwrite {receipt}")
    remix = args.remix or ("send-return-poc" if args.post_fader else "bus")
    mods = registry.bound(registry.remix(remix))
    hosts = [Host(image, tag, work, mods, args.host, False, post_fader=args.post_fader, inmask=15)
             for tag, image in (("baseline", args.baseline), ("candidate", args.candidate))]
    report = dict(script_sha256=sha(Path(__file__)), harness_sha256=sha(ROOT / "tools/verify/verify_bus_dsp_identity.py"),
                  baseline=dict(path=str(args.baseline), sha256=sha(args.baseline)),
                  candidate=dict(path=str(args.candidate), sha256=sha(args.candidate)),
                  host=dict(path=str(args.host), sha256=sha(args.host)), remix=remix,
                  post_fader=args.post_fader,
                  tagged_transition_scope="constant raw words only; isolated SEND and real firmware gates cover transitions",
                  extraction={h.tag: [sha(p) for p in h.mems] for h in hosts},
                  memory_scope=dict(y_words=0x40000, excluded_y_words=0,
                                    program_memory_captured=False,
                                    harness="P and Y are separate below the $200000 bridge"),
                  meter_unit="executed instructions, not hardware cycles", cases=[], controls=[])
    selected = [row for row in cases(args.post_fader) if not args.only or args.only in row[0].name]
    if not selected:
        ap.error("no selected cases")
    saved = {}
    for case, target, words in selected:
        before, a, state_a, y_a = capture(hosts[0], case, target, words)
        after, b, state_b, y_b = capture(hosts[1], case, target, words)
        checks = dict(input_identical=before["input_sha256"] == after["input_sha256"],
                      raw24_identical=a == b, state_identical=state_a == state_b,
                      **compare_y_data(y_a, y_b))
        weights = {}
        if target == 0:
            weights = {"baseline": reverb_weights(state_a, y_a),
                       "candidate": reverb_weights(state_b, y_b)}
            checks["reverb_injection_weights"] = all(
                row == [0, 0, 0, 0x7f0000, 0, 0, 0, 0x810000] for row in weights.values())
        if state_a != state_b:
            differences = [(x[0], off, old, new) for x, y in zip(state_a, state_b)
                           for off, (old, new) in enumerate(zip(x[1:], y[1:])) if old != new]
        else:
            differences = []
        report["cases"].append(dict(name=case.name, split=case.split, events=case.events,
            changes=case.changes, captured_instance=target, checks=checks,
            final_reverb_injection_weights=weights,
            first_state_differences=differences[:16], baseline=before, candidate=after,
            saved_instructions_per_frame=[x-y for x, y in zip(before["instructions_per_sample"], after["instructions_per_sample"])]))
        saved[case.name] = (before, state_a, y_a)
        print(f"[{'PASS' if all(checks.values()) else 'FAIL'}] {case.name}: {checks}; "
              f"saved/frame {report['cases'][-1]['saved_instructions_per_frame']}", flush=True)
        receipt.write_text(json.dumps(report, indent=2) + "\n")
    for name, (result, state, ydata) in saved.items():
        control = transition_controls(name, state, ydata)
        if control:
            report["controls"].append(control)
    for split in (0, 7):
        zero, active = f"send_d0_r0_s{split}", f"send_d127_r127_s{split}"
        if zero in saved and active in saved:
            changed = all(saved[zero][0]["hashes"][i] != saved[active][0]["hashes"][i] for i in (0, 2))
            report["controls"].append(dict(name=f"both sends change wet audio split{split}", passed=changed))
    report["passed"] = all(all(c["checks"].values()) for c in report["cases"]) and all(c["passed"] for c in report["controls"])
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {len(selected)} pairs; {receipt}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
