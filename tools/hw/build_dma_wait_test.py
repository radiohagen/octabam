#!/usr/bin/env python3
"""Build the opt-in 8192/4096 BusDelay wait pair; never touch a card or device.

    python3 tools/hw/build_dma_wait_test.py --out out/dma-wait-20261031

Uses the existing DLSRC hatch with a generated source, leaving the normal
module and build defaults unchanged. Run alone: the standard builder owns
out/mainos_bus.bin and out/dsp. Outputs are experimental RMX images, build
logs and provenance, NOT evidence of safe hardware DMA timing. Follow the
audio/state and hardware qualification in BUS_DSP_OPTIMIZATION.md section 10.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import toolpath  # noqa: E402,F401
from remix import registry  # noqa: E402

REMIX, BUILD = "test/send-return-poc", "D1"
BASE_NAME, TEST_NAME = "BUS DMA8K", "BUS DMA4K"
SOURCE = ROOT / "modules/busdelay/delay_server.asm"
PAD = ("        move    #>$2000,x0\n"
       "        do      x0,pad_end\n"
       "        nop\n"
       "pad_end:\n")


def half_wait(source):
    """Fail closed on source drift; the only edit is the nonzero DO count."""
    if source.count(PAD) != 1:
        raise ValueError("expected exactly one complete 8192-NOP read-back pad")
    return source.replace(PAD, PAD.replace("$2000", "$1000"), 1)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args, env, log):
    with log.open("w") as output:
        result = subprocess.run(args, cwd=ROOT, env=env, stdout=output,
                                stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}); see {log}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True,
                    help="new directory under this worktree's ignored out/")
    args = ap.parse_args()
    work = args.out.resolve()
    if not work.is_relative_to((ROOT / "out").resolve()) or work.exists():
        ap.error("--out must be a new directory below this worktree's out/")
    source = SOURCE.read_text()
    candidate = half_wait(source)
    remix = registry.remix(REMIX)
    if remix.grains != 4:
        ap.error("this experiment requires the four-grain integration fixture")
    work.mkdir(parents=True)
    (work / "delay-8192.asm").write_text(source)
    alternate = work / "delay-4096.asm"
    alternate.write_text(candidate)

    # Do not inherit DSP probes, source overrides or environment tuning.
    # Keep the toolchain's normal executable search and OS temp directory.
    env = {key: os.environ[key] for key in (
        "PATH", "HOME", "TMPDIR", "USER", "LOGNAME", "LANG", "LC_ALL",
        "LC_CTYPE", "DEVELOPER_DIR", "SDKROOT") if key in os.environ}
    env.update(REMIX=REMIX, BUILD=BUILD, XBUS="1", SPEC="1")
    report = dict(
        experimental=True, hardware_accepted=False, remix=REMIX, build=BUILD,
        grains=remix.grains,
        source_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        source_status=subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True).splitlines(),
        modules=list(remix.modules),
        source_sha256=sha(SOURCE), alternate_sha256=sha(alternate),
        tool_sha256={name: sha(ROOT / name) for name in (
            "tools/build/build_bus.py", "tools/build/make_rmx.py",
            "tools/hw/build_dma_wait_test.py",
            "tools/verify/verify_dma_wait.py", "tools/harness/image_dsp.py",
            "vendor/dsp56300/build/source/dsp_host/dsp_asm",
            "vendor/dsp56300/build/source/disassemble/dsp56kDisassemble")},
        builds=[])
    rows = (("baseline", BASE_NAME, None, 8192),
            ("candidate-matched-name", BASE_NAME, alternate, 4096),
            ("candidate", TEST_NAME, alternate, 4096))
    for tag, name, override, count in rows:
        print(f"Building {tag}: {name}, {count} NOPs/call", flush=True)
        build_env = dict(env, RMXNAME=name)
        if override:
            build_env["DLSRC"] = str(override)
        cmd = [sys.executable, "tools/build/build_bus.py"]
        command(cmd, build_env, work / f"{tag}-build.log")
        image = work / f"{tag}.bin"
        shutil.copyfile(ROOT / "out/mainos_bus.bin", image)
        report["builds"].append(dict(
            tag=tag, name=name, wait_nops=count, command=cmd,
            build_settings={k: build_env[k] for k in
                            ("REMIX", "BUILD", "XBUS", "SPEC", "RMXNAME", "DLSRC")
                            if k in build_env},
            image=str(image.relative_to(work)), bytes=image.stat().st_size,
            sha256=sha(image)))
        if SOURCE.read_text() != source:
            raise RuntimeError("normal delay source changed during the experiment")
    from verify_dma_wait import verify_pair, verify_label_pair
    report["same_name_binary_proof"] = verify_pair(
        work / "baseline.bin", work / "candidate-matched-name.bin")
    report["package_label_proof"] = verify_label_pair(
        work / "candidate-matched-name.bin", work / "candidate.bin", BASE_NAME, TEST_NAME)
    # Labels are built through the normal RMXNAME path, never binary-patched.
    # The paired audio gates below must use the final labelled package images.
    package = work / "package/BRAIN/REMIXES"
    package.mkdir(parents=True)
    for tag, name in (("baseline", BASE_NAME), ("candidate", TEST_NAME)):
        image = work / f"{tag}.bin"
        command([sys.executable, "tools/build/make_rmx.py", str(image), name],
                env, work / f"{tag}-rmx.log")
        destination = package / f"{name}.RMX"
        shutil.copyfile(ROOT / "out" / f"{name}.RMX", destination)
        if sha(destination) != sha(image):
            raise RuntimeError("RMX packaging changed the verified raw image")
    (work / "build-receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Built {package}; audio/state and physical timing qualification remain.")


if __name__ == "__main__":
    main()
