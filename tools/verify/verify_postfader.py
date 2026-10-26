#!/usr/bin/env python3
"""POST FADER on the current firmware and DSPs, adapted from PR 542.

Stages owned copies with T7 silent but its original sends held at 100.
Muting, fading or solo-excluding that track must leave the remaining
sender's return bit-identical. Changing T7's original send to zero is a
positive control: it changes participation, so the return must differ.
Only T2 has sample trigs; the provided project must have audible T2 audio.
The installed-hook gate separately covers every LEVEL and transient tag.

Does not establish physical timing, instantaneous mute, or crossfader XLV.
Existing effect state is retained; SEND's normal smoothing remains.
"""
import argparse, contextlib, os, pathlib, re, shutil, subprocess, sys, wave
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1])); import toolpath  # noqa: E402,F401
from remix import registry  # noqa: E402
import ot_project as otp  # noqa: E402
import blockdump as bd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
EMU = ROOT / "out/emu/ot_emu"
PY = ROOT / ".venv/bin/python3"
OUT = ROOT / "out/postfaderverify"
FRAMES, WARM, MUTE_FRAME = 2000, 1200, 1000
FIXTURES = (("baseline", 100), ("muted", 100), ("faded", 100), ("solo", 100),
            ("membership", 0), ("source_muted", 100), ("tail", 100), ("tail_t1", 100),
            ("tail_t2", 100), ("tail_t5", 100))
RETURNS_RB = ((1, (0x80003190, 0x80003590), 0, "T1"), (0, (0x80003390, 0x80003790), 0, "T5"))


def stage(template, remix, tag, t7, audio):
    d = OUT / tag
    shutil.rmtree(d, ignore_errors=True)
    (d / "project").mkdir(parents=True)
    for f in template.iterdir():
        if f.is_file() and f.suffix.lower() in (".work", ".strd"):
            shutil.copy2(f, d / "project" / f.name)
    p = d / "project"
    otp.host_rig(p, remix, guard=False)
    mods = registry.bound(registry.remix(remix))
    send = mods["SEND"].menu.fx2_id
    for slot in ("0", "1"):
        for key in ("SEND", "DELAY SERVER", "REVERB SERVER"):
            otp.stamp_slot(p, str(mods[key].menu.fx2_id), slot, 100, guard=False)
        otp.stamp_slot(p, str(send), slot, t7, guard=False, tracks={7})

    def free(data):
        # locks on FX2 slots 0-1 (lock slots 24, 25) and LFOs on them would
        # move the knobs the records are checked against
        for pat in range(16):
            for t in range(8):
                if t != 1:
                    # Clear sample triggers on every source except T2. This
                    # makes T7's changed fader unable to change dry audio.
                    start = otp.trac_off(pat, t)
                    data[start:start+8] = bytes(8)
                base = otp.trac_off(pat, t) + 0x59
                for st in range(64):
                    data[base + st * 32 + 24] = 0xff
                    data[base + st * 32 + 25] = 0xff
        for part in range(otp.NPARTS_ALL):
            off = otp.PART_BASE + part * otp.PART_STRIDE
            # Documented track LEVEL halfword: high byte carries the level.
            data[off + 0x1b + 2*6] = 0 if tag == "faded" else 127
            for t in range(8):
                lfo = otp.PART_BASE + part * otp.PART_STRIDE + otp.LFO_PM_OFF + t * 30
                for k in range(3):
                    if data[lfo + k] in (24, 25):
                        data[lfo + k] = 18
    for bw in sorted(p.glob("bank*.work")):
        otp._bank_write(p, int(bw.name[4:6]), free, guard=False)
    raw = (p / "project.work").read_bytes()
    if "RETURNS" in registry.remix(remix).modules:
        raw = raw.replace(b"MASTER_TRACK=0", b"MASTER_TRACK=1")
    else:
        raw = raw.replace(b"MASTER_TRACK=1", b"MASTER_TRACK=0")
    for track in range(8):
        raw, count = re.subn(rb"(?m)^MIDI_TRIG_CH" + str(track+1).encode() + rb"=-?\d+",
                            f"MIDI_TRIG_CH{track+1}={track}".encode(), raw)
        assert count == 1, "fixture needs eight track MIDI channel settings"
    # Own the mute state; do not rely on an arbitrary user's template.
    mute = 64 if tag == "muted" else 2 if tag == "source_muted" else 0
    raw, nm = re.subn(rb"(?m)^TRACK_MUTE_MASK=\d+", f"TRACK_MUTE_MASK={mute}".encode(), raw)
    raw, ns = re.subn(rb"(?m)^TRACK_SOLO_MASK=\d+", (b"TRACK_SOLO_MASK=2" if tag == "solo" else b"TRACK_SOLO_MASK=0"), raw)
    assert nm == ns == 1, "fixture must contain audio mute/solo masks"
    (p / "project.work").write_bytes(re.sub(rb"\r\nPATTERN=\d+\r\n", b"\r\nPATTERN=0\r\n", raw))
    cmd = [str(PY), str(ROOT / "tools/emu/ot_emu/stage_card.py"), str(p), "OCTABAM", "PF",
           "--tree", str(d / "tree"), "--out", str(d / "card.img"), "--image-mb", "64"]
    for a in audio:
        cmd += ["--audio", a]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"verify_postfader: stage_card {tag} failed:\n{r.stdout[-800:]}{r.stderr[-800:]}")


def run(image, tag):
    d = OUT / tag
    cmd = [str(EMU), "--image", str(image), "--card", str(d / "card.img"), "--set", "OCTABAM",
           "--project", "PF", "--sequencer", "--internal-clock", "--frames", str(FRAMES),
           "--load-ms", "90000", "--dsp", "--main-level", "64",
           "--poke", "0x80000049=1",       # audio CC input enabled
           "--block-dump", str(d / "blocks.dump"),
           "--mem-dump", f"0x80000000,0x8000={d / 'sram.bin'}"]
    if tag.startswith("tail_t"):
        track = int(tag[6:])
        midi = d / "mute.midi"
        midi.write_text(f"{MUTE_FRAME} {0xaf+track:02X} 31 7F\n")
        cmd += ["--midi", str(midi)]
    with open(d / "run.txt", "w") as f:
        r = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    return tag, r.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("remix", nargs="?", default=os.environ.get("REMIX"))
    ap.add_argument("--project", default=os.environ.get("OT_PROJECT", ""))
    ap.add_argument("--image", default="")
    a = ap.parse_args()
    remix = registry.remix(a.remix)
    if "POST FADER" not in remix.modules:
        print(f"  [ -- ] verify_postfader: {a.remix} carries no POST FADER"); return 0
    if not a.project:
        print("  [SKIP] verify_postfader: no project (OT_PROJECT=<dir> or --project)"); return 0
    if not EMU.is_file():
        print("  [SKIP] verify_postfader: no port binary (make emu-cf)"); return 0
    template = pathlib.Path(a.project).expanduser()
    if not (template / "project.work").is_file():
        sys.exit(f"verify_postfader: {template} is not a project")
    OUT.mkdir(parents=True, exist_ok=True)
    # Reuse the existing deterministic FLEX fixture, always under owned out/.
    generated = OUT / "source"
    shutil.rmtree(generated, ignore_errors=True)
    r = subprocess.run([str(PY), str(ROOT / "tools/harness/usb_sig_project.py"),
                        "--source", str(template), "--out", str(generated)],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        sys.exit(f"verify_postfader: tone fixture failed:\n{(r.stdout+r.stderr)[-1500:]}")
    template = generated
    burst = OUT / "burst.wav"
    with wave.open(str(template / "AUDIO/USBSIG/T2.wav"), "rb") as w:
        params, samples = w.getparams(), w.readframes(w.getnframes())
    # 200 ms excites the already-warm engines; silence precedes the mute by
    # 160 ms, so any difference after it is a changed tail, not dry audio.
    cutoff = 8820 * 4
    with wave.open(str(burst), "wb") as w:
        w.setparams(params)
        w.writeframes(samples[:cutoff] + bytes(len(samples)-cutoff))
    image = OUT / "mainos.bin"
    if a.image:
        source = pathlib.Path(a.image).resolve()
        if source != image.resolve():
            shutil.copy2(source, image)
    else:
        env = dict(os.environ, REMIX=a.remix, XBUS="1", SPEC="1"); env.setdefault("BUILD", "0")
        r = subprocess.run([sys.executable, str(ROOT / "tools/build/build_bus.py")], env=env,
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode:
            sys.exit(f"verify_postfader: building {a.remix} failed:\n{(r.stdout + r.stderr)[-1500:]}")
        shutil.copy2(ROOT / "out/mainos_bus.bin", image)
    audio = [f"{template / 'AUDIO/USBSIG' / f'T{t}.wav'}:AUDIO/USBSIG/T{t}.wav" for t in range(1, 9)]
    for tag, t7 in FIXTURES:
        fixture_audio = [f"{burst}:AUDIO/USBSIG/T2.wav" if tag.startswith("tail") and s.endswith("/T2.wav") else s for s in audio]
        with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet):
            stage(template, a.remix, tag, t7, fixture_audio)
        print(f"  staged {tag}", flush=True)
    with ThreadPoolExecutor(2) as ex:
        codes = dict(ex.map(lambda f: run(image, f[0]), FIXTURES))

    fails = 0

    def check(msg, ok):
        nonlocal fails
        print(f"  [{'ok' if ok else 'FAIL'}] {msg}")
        fails += not ok

    for tag, code in codes.items():
        check(f"{tag}: {FRAMES} frames ran (exit {code})", code == 0)
    if fails:
        print(f"verify_postfader: FAIL ({fails})"); return 1

    mods = registry.bound(remix)
    send_id, dly_id = mods["SEND"].menu.fx2_id, mods["DELAY SERVER"].menu.fx2_id
    d = (OUT / "muted" / "sram.bin").read_bytes()
    u16 = lambda addr: int.from_bytes(d[addr - 0x80000000:addr - 0x80000000 + 2], "big")
    u32 = lambda addr: int.from_bytes(d[addr - 0x80000000:addr - 0x80000000 + 4], "big")
    rec = 0x80000110 + (u32(0x800000e0) << 9)
    mix = u32(0x80003c10)
    for t in range(8):
        fid = u16(rec + 64 * t + 56)
        lvl = u16(mix + 8 * t + 2) >> 8
        s0, s1 = u16(rec + 64 * t + 24), u16(rec + 64 * t + 26)
        if fid in (send_id, 0):
            want = ((100 << 8) * lvl * lvl >> 14) | 0x8000
            check(f"T{t + 1} SEND at L {lvl}: DEL/REV {s0:04x}/{s1:04x}, want {want:04x}"
                  + (" (muted: participation only)" if lvl == 0 else ""), s0 == want and s1 == want)
        elif t == 7:
            check(f"T8 (FX2 id {fid:#x}, not a send) keeps its knobs ({s0:04x}/{s1:04x})",
                  fid not in (send_id, 0, dly_id))
    check("T7 is muted in the fixture (its MAIN gain reads 0)", u16(mix + 8 * 6 + 2) == 0)

    outputs = ((0, (0x80003390, 0x80003790), 3, "T8 returns"),) if "RETURNS" in remix.modules else RETURNS_RB
    muted = bd.classes(bd.read(OUT / "source_muted" / "blocks.dump"))
    for core, rams, ti, name in outputs:
        values = [w[64*ti:64*ti+64] for ram in rams
                  for f, w in muted.get(('<', 1, core, ram), []) if f > WARM]
        check(f"muted active source: {name} stays silent ({len(values)} frames)",
              len(values) > 100 and not any(any(w) for w in values))
    for left, right, equal in (("baseline", "muted", True), ("baseline", "faded", True),
                               ("baseline", "solo", True), ("baseline", "membership", False),
                               ("tail", "tail_t1", True), ("tail", "tail_t2", True),
                               ("tail", "tail_t5", True)):
        A = bd.classes(bd.read(OUT / left / "blocks.dump"))
        B = bd.classes(bd.read(OUT / right / "blocks.dump"))
        for core, rams, ti, name in outputs:
            n = k = nonzero = 0
            for ram in rams:
                sa = {f: w for f, w in A.get(('<', 1, core, ram), [])}
                sb = {f: w for f, w in B.get(('<', 1, core, ram), [])}
                for f in sa.keys() & sb.keys():
                    if f > WARM:
                        n += 1
                        x, y = sa[f][64 * ti:64 * ti + 64], sb[f][64 * ti:64 * ti + 64]
                        k += x != y
                        nonzero += any(x) or any(y)
            check(f"{left}/{right}: {name} {'identical' if equal else 'DIFFERS with changed original participation'} "
                  f"({k}/{n} frames differ; {nonzero} non-silent)",
                  n > 100 and nonzero > 100 and ((k == 0) if equal else (k > 0)))
    solo = (OUT / "solo" / "sram.bin").read_bytes()
    mix = int.from_bytes(solo[0x3c10:0x3c14], "big") - 0x80000000
    check("solo fixture keeps T2 audible and zeros T7 MAIN gain",
          int.from_bytes(solo[mix+10:mix+12], "big") > 0
          and solo[mix+50:mix+52] == bytes(2))
    faded = (OUT / "faded" / "sram.bin").read_bytes()
    mix = int.from_bytes(faded[0x3c10:0x3c14], "big") - 0x80000000
    check("faded fixture zeros T7 MAIN gain", faded[mix+50:mix+52] == bytes(2))
    for track in (1, 2, 5):
        tail = (OUT / f"tail_t{track}" / "sram.bin").read_bytes()
        mix = int.from_bytes(tail[0x3c10:0x3c14], "big") - 0x80000000
        check(f"dynamic T{track} mute reached the real mixer snapshot",
              tail[mix + 8*(track-1)+2:mix + 8*(track-1)+4] == bytes(2))
    print(f"verify_postfader: {'ok' if not fails else 'FAIL'} ({fails} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
