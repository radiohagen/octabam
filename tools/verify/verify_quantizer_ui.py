#!/usr/bin/env python3
"""Exercise TRACK -> CHROMATIC from the panel in audio and MIDI on both models.

Regression for #741: MIDI branches into the audio hook's last instruction.
The runtime must keep stock's shared stack push at 0x400449be. No hardware
or audio claim: this checks the panel path, its draw and the running state.
"""
import os
import pathlib
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import toolpath  # noqa: E402,F401
from remix import registry  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    remix = sys.argv[1]
    if "SCALE QUANTIZER" not in registry.remix(remix).modules:
        return 0
    project = os.environ.get("OT_PROJECT", "")
    if not project:
        cfg = pathlib.Path("~/.octabam_project").expanduser()
        project = cfg.read_text().strip() if cfg.exists() else ""
    out = ROOT / "out/quantizer-ui"
    out.mkdir(parents=True, exist_ok=True)
    if not project:
        empty = out / "empty-project"
        empty.mkdir(exist_ok=True)
        project = str(empty)            # stock initialises the absent bank files
    env = dict(os.environ, REMIX=remix, XBUS="1", SPEC="1")
    subprocess.run([sys.executable, "tools/build/build_bus.py"], cwd=ROOT, env=env,
                   stdout=subprocess.DEVNULL, check=True)
    image = out / "mainos.bin"
    shutil.copy2(ROOT / "out/mainos_bus.bin", image)
    installed = image.read_bytes()
    assert installed[0x400449be - 0x40000400:0x400449c0 - 0x40000400] == bytes.fromhex("2f00")
    card = out / "card.img"
    subprocess.run([str(ROOT / ".venv/bin/python3"), "tools/emu/ot_emu/stage_card.py",
                    project, "QZSET", "QZPRJ", "--out", str(card)], cwd=ROOT,
                   stdout=subprocess.DEVNULL, check=True)
    fails = 0
    for model in ("mki", "mkii"):
        cmd = [str(ROOT / "out/emu/ot_emu"), "--image", str(image), "--card", str(card),
               "--set", "QZSET", "--project", "QZPRJ", "--load-ms", "90000",
               "--watch-pc", "0x400bf10a,0x400449be"]
        if model == "mkii":
            cmd += ["--mkii"]
        for midi in (False, True):
            tag = f"{model}-{'midi' if midi else 'audio'}"
            script = out / f"{tag}.script"
            lines, t = [], 1500

            def send(text, gap=150):
                nonlocal t
                lines.append(f"{t} {text}")
                t += gap

            def tap(key):
                send(f"key {key:#x} down", 40)
                send(f"key {key:#x} up", 300)

            tap(0x32)
            if midi:
                tap(0x35)
            send("key 0x2d down")
            tap(0x20)                 # open the list on TRACK
            tap(0x20)                 # CHROMATIC: its redraw used to corrupt sp
            send("key 0x2d up", 500)
            tap(0x31)
            send("quit")
            script.write_text("\n".join(lines) + "\n")
            state = out / f"{tag}.state"
            mode = out / f"{tag}.mode"
            log = out / f"{tag}.log"
            cmd += ["--scenario", f"{log} --live-script {script} "
                    f"--poke 0x80000012=00;0x80000013=00;0x80000014=00;0x80000015=00;"
                    f"0x460d16f0=00;0x460d16f1=00;0x460d16f2=00;0x460d16f3=00 "
                    f"--mem-dump 0x460d16f0,4={state};0x80000012,4={mode}"]
        with (out / f"{model}.log").open("w") as f:
            subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, check=True)
        for midi in (False, True):
            tag = f"{model}-{'midi' if midi else 'audio'}"
            log = (out / f"{tag}.log").read_text()
            state = struct.unpack(">I", (out / f"{tag}.state").read_bytes())[0]
            mode = struct.unpack(">I", (out / f"{tag}.mode").read_bytes())[0]
            ok = "ended on quit" in log and "at 0x400bf10a" not in log and state == 1 and mode == int(midi)
            if midi:
                ok &= "at 0x400449be" in log
            print(f"  [{'PASS' if ok else 'FAIL'}] verify_quantizer_ui: {tag} selects CHROMATIC, draws and returns cleanly")
            fails += not ok
    return int(bool(fails))


if __name__ == "__main__":
    sys.exit(main())
