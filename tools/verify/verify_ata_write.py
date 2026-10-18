#!/usr/bin/env python3
"""Force the first-sector completion IRQ against the actual selected image.

The stock control must expose stale bookkeeping; the guarded image must
defer the interrupt. No physical-card timing or hardware claim is made.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import toolpath  # noqa: E402,F401
from remix import registry  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("remix")
    a = ap.parse_args()
    if "ATA WRITE GUARD" not in registry.remix(a.remix).modules:
        print(f"  [ -- ] {a.remix} has no ATA WRITE GUARD")
        return 0
    work = ROOT / "out/ata_write_probe"
    # Own build directory: the shared installed port contains executables,
    # not a linkable library, and must never be modified for one module.
    for cmd in (["cmake", "-S", str(ROOT / "tools/harness/ata_write_probe"),
                 "-B", str(work), "-DCMAKE_BUILD_TYPE=Release"],
                ["cmake", "--build", str(work), "--target", "ata_write_probe", "-j4"]):
        built = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if built.returncode:
            sys.exit("verify_ata_write: probe build failed:\n" +
                     (built.stdout + built.stderr)[-3000:])
    probe = work / "ata_write_probe"
    env = dict(os.environ, REMIX=a.remix, XBUS="1", SPEC="1")
    env.setdefault("BUILD", "0")
    built = subprocess.run([sys.executable, "tools/build/build_bus.py"], cwd=ROOT,
                           env=env, capture_output=True, text=True)
    if built.returncode:
        sys.exit("verify_ata_write: build failed:\n" + (built.stdout + built.stderr)[-2000:])
    layout = json.loads((ROOT / "out/platform/layout.json").read_text())
    return subprocess.run([str(probe), str(ROOT / "out/raw/section_3_MAIN_OS.bin"),
                           str(ROOT / "out/mainos_bus.bin"),
                           str(ROOT / "out/platform/runtime/runtime.bin"),
                           hex(layout["base"])], cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())
