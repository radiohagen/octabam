#!/usr/bin/env python3
"""Repeat the integrated boot with dirty runtime memory and both DSPs.

Host-side diagnostic only: never opens hardware or writes a device. The
port has no cache/electrical model, so passing is not hardware acceptance.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import toolpath  # noqa: E402,F401 -- repository toolchain lookup

OUT = ROOT / 'out/midi-boot'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    image = OUT/'candidate.bin'
    image.write_bytes((ROOT/'out/mainos_bus.bin').read_bytes())
    layout = json.loads((ROOT/'out/platform/layout.json').read_text())
    raw = subprocess.check_output(['m68k-elf-nm', str(ROOT/'out/platform/loader.elf')], text=True)
    symbols = {f[2]: int(f[0], 16) for line in raw.splitlines() if len(f := line.split()) == 3}
    stages = {symbols['octabam_bootstrap']: 'loader', symbols['fatal']: 'loader-fatal',
              0x40001e50: 'DSP-upload', 0x40000512: 'runtime-loaded',
              0x4001f834: 'panel-init', 0x4001f4dc: 'panel-handshake',
              0x4000aad0: 'audio-frame'}
    version = OUT/'nor-version.bin'
    version.write_bytes((ROOT/'out/raw/section_3_MAIN_OS.bin').read_bytes()[0xde648:0xde64a])
    results = []
    for name, byte in (('zero', 0), ('ff', 255), ('a5', 165)):
        fill = OUT/f'{name}-arena.bin'
        fill.write_bytes(bytes([byte])*(layout['bss_end']-layout['base']))
        cmd = [str(ROOT/'out/emu/ot_emu'), '--image', str(image), '--mkii',
               '--dsp', '--frame', '--ms', '5000', '--boot-logo', '--max', '150000000',
               # Repeated --preload options replace each other; use ONE list.
               '--preload', f'{layout["base"]:#x}={fill};0x3ffc={version}',
               '--watch-pc', ','.join(hex(a) for a in stages)]
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
        log = r.stdout+r.stderr
        (OUT/f'{name}.log').write_text(log)
        seen = [stages[int(a, 16)] for a in re.findall(r'at 0x([0-9a-f]+) d0=', log)
                if int(a, 16) in stages]
        loaded = all(str(path) in log for path in (fill, version))
        passed = (r.returncode == 0 and loaded and 'HANDOFF' in log
                  and 'loader-fatal' not in seen and seen.count('loader') == 1
                  and 'M6a gate   : PASS' in log
                  and 'core 0: boot ROM done' in log and 'core 1: boot ROM done' in log
                  and 'runtime-loaded' in seen and 'panel-handshake' in seen and 'audio-frame' in seen)
        results.append(dict(fill=name, passed=passed, returncode=r.returncode,
                            both_preloads_seen=loaded, stages=seen))
        receipt = dict(image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                       tests=results, hardware_tested=False,
                       scope='Port: dirty arena, native boot logo, DSP upload, panel handshake and audio frames; no cache or electrical model')
        (OUT/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
        assert passed, f'{name}: see {OUT/name}.log'
        print(f'[ok] {name}: dirty runtime, native logo, both DSPs, panel and audio frames', flush=True)


if __name__ == '__main__':
    main()
