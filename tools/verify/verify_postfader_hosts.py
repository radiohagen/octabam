#!/usr/bin/env python3
"""Sounding T1/T5 host mutes through the real firmware and both DSPs.

Only the selected host plays a continuous generated tone from the first trig.
A saved mute must leave its dry DSP audio alive, zero both send gains while
retaining participation, and produce no wet return. An unmuted counterpart
must excite BOTH wet-only buffers, so master dry audio cannot pass the control.
Uses owned project copies; no image build, source project edit or hardware claim.
Immediate onset catches an init-packet target incorrectly seeding the send ramp
through warmup; dynamic mute/tail preservation is covered by verify_postfader.py.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import toolpath  # noqa: E402,F401
import verify_postfader as pf

PEEKS = '0:Y:e00,32;0:Y:e24,1;0:Y:9f0,1;0:Y:9f4,2;1:Y:30100,256;1:X:6265,1'
CASES = tuple((track, muted) for track in (1, 5) for muted in (False, True))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assess(root, track, muted, code):
    tag = f't{track}_{"muted" if muted else "audible"}'
    folder = root / tag
    packets = pf.bd.classes(pf.bd.read(folder/'blocks.dump'))
    sram = (folder/'sram.bin').read_bytes()
    core = 1 if track == 1 else 0
    audio_bases = (0x80003190, 0x80003590) if core else (0x80003390, 0x80003790)
    param_bases = (0x80000110, 0x80000310) if core else (0x80000210, 0x80000410)
    # Both hosts are the first slot on their core. Read-back carries two
    # halfwords per sample; the 64-word track slice is 16 stereo frames.
    dry = [w[:64] for base in audio_bases
           for frame, w in packets.get(('<', 1, core, base), []) if frame > pf.WARM]
    controls = [w[12:14] for base in param_bases
                for frame, w in packets.get(('>', 0, core, base), []) if frame > pf.WARM]
    output = [w[192:256] for base in (0x80003390, 0x80003790)
              for frame, w in packets.get(('<', 1, 0, base), []) if frame > pf.WARM]
    mix = int.from_bytes(sram[0x3c10:0x3c14], 'big') - 0x80000000
    level = int.from_bytes(sram[mix+8*(track-1)+2:mix+8*(track-1)+4], 'big')
    seen = {}
    log = (folder/'run.txt').read_text()
    for c, space, address, values in re.findall(r'core (\d) ([XYP]):(0x[0-9a-f]+): ([0-9a-f ]+)', log):
        seen[int(c), space, int(address, 16)] = [int(v, 16) for v in values.split()]
    rv, dl = seen.get((0, 'Y', 0xe00), []), seen.get((1, 'Y', 0x30100), [])
    checks = {
        'firmware completed': code == 0,
        'stock OT mute semantics': sram[0xdc:0xe0] == bytes(4),
        'MASTER enabled': sram[0x34] == 1,
        'host dry keeps sounding': len(dry) > 100 and sum(any(w) for w in dry) > 100,
        'both send controls observed': len(controls) > 100,
        'both original sends retain participation': bool(controls) and all(d & 0x8000 and r & 0x8000 for d, r in controls),
        'independent reverb routing active': seen.get((0, 'Y', 0xe24)) == [0x5a5a5a],
        'independent delay routing active': seen.get((1, 'X', 0x6265), [0])[0] in (1, 2, 3),
        'complete wet buffer snapshots': len(rv) == 32 and len(dl) == 256,
    }
    rev_mask = 0x7f00 if track == 1 else 0x7fff
    if muted:
        checks.update({
            'saved mute reached mixer': level == 0,
            'both send coefficients stay zero': bool(controls) and all(d == 0x8000 and not r & rev_mask for d, r in controls),
            'master output stays silent after warmup': len(output) > 100 and not any(any(w) for w in output),
            'reverb wet stays silent': len(rv) == 32 and not any(rv),
            'delay wet stays silent': len(dl) == 256 and not any(dl),
        })
        if track == 5:
            checks['reverb own REV coefficient is zero'] = seen.get((0, 'Y', 0x9f0)) == [0]
            checks['reverb own DEL ramp and step are zero'] = seen.get((0, 'Y', 0x9f4)) == [0, 0]
    else:
        checks.update({
            'unmuted mixer gain is live': level > 0,
            'both send coefficients are live': bool(controls) and all(d & 0x7fff and r & rev_mask for d, r in controls),
            'reverb positive control has wet audio': len(rv) == 32 and any(rv),
            'delay positive control has wet audio': len(dl) == 256 and any(dl),
        })
    for name, ok in checks.items():
        print(f'  [{"ok" if ok else "FAIL"}] {tag}: {name}', flush=True)
    return dict(name=tag, passed=all(checks.values()), checks=checks,
                compared_frames=len(output), nonzero_dry_frames=sum(any(w) for w in dry),
                parameter_frames=len(controls), mixer_gain=level,
                reverb_wet_nonzero_words=sum(bool(w) for w in rv),
                delay_wet_nonzero_words=sum(bool(w) for w in dl),
                blocks_sha256=sha(folder/'blocks.dump'), snapshot_sha256=sha(folder/'sram.bin'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('remix', nargs='?', default='test/send-return-poc')
    ap.add_argument('--image', type=Path, default=pf.ROOT/'out/mainos_bus.bin')
    ap.add_argument('--project', type=Path, default=os.environ.get('OT_PROJECT'),
                    help='local structural template; copied into owned scratch (or OT_PROJECT)')
    a = ap.parse_args()
    r = pf.registry.remix(a.remix)
    if not {'POST FADER', 'RETURNS', 'REVERB SERVER', 'DELAY SERVER'}.issubset(r.modules):
        print('[ -- ] host mute gate needs POST FADER, RETURNS and both bus engines')
        return 0
    if a.project is None:
        print('[SKIP] host mute gate: use --project TEMPLATE or OT_PROJECT')
        return 0
    if not pf.EMU.is_file():
        print('[SKIP] host mute gate: no port binary (make emu-cf)')
        return 0
    if not a.image.is_file() or not (a.project/'project.work').is_file():
        ap.error('image and local project.work must exist')
    pf.OUT = root = pf.ROOT/'out/postfaderhosts'
    root.mkdir(parents=True, exist_ok=True)
    generated = root/'source'
    if a.project.resolve() == generated.resolve():
        ap.error('use a template outside this gate\'s owned source directory')
    shutil.rmtree(generated, ignore_errors=True)
    command = [str(pf.PY), str(pf.ROOT/'tools/harness/usb_sig_project.py'),
               '--source', str(a.project.resolve()), '--out', str(generated)]
    run = subprocess.run(command, cwd=pf.ROOT, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError((run.stdout+run.stderr)[-2000:])
    image = root/'mainos.bin'
    if a.image.resolve() != image.resolve():
        shutil.copy2(a.image, image)
    report = dict(remix=a.remix, image=str(a.image.resolve()), image_sha256=sha(image),
                  emulator_sha256=sha(pf.EMU), script_sha256=sha(__file__),
                  helper_sha256=sha(pf.__file__), cases=[],
                  mute_delivery='saved project mask before DSP initialization',
                  source_onset_samples=0,
                  limits='OT mute mode; MASTER on; no physical timing or active-return split acceptance')
    audio = [f'{generated / "AUDIO/USBSIG" / f"T{t}.wav"}:AUDIO/USBSIG/T{t}.wav' for t in range(1, 9)]
    report['source_audio_sha256'] = {f'T{t}': sha(generated/f'AUDIO/USBSIG/T{t}.wav') for t in (1, 5)}
    for track, muted in CASES:
        tag = f't{track}_{"muted" if muted else "audible"}'
        with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet):
            pf.stage(generated, a.remix, tag, 100, audio, source_track=track,
                     mute_mask=(1 << (track-1)) if muted else 0)
        print(f'staged {tag}', flush=True)
    def execute(pair):
        track, muted = pair
        tag = f't{track}_{"muted" if muted else "audible"}'
        _, code = pf.run(image, tag, dsp_peek=PEEKS)
        return assess(root, track, muted, code)
    with ThreadPoolExecutor(2) as pool:
        report['cases'] = list(pool.map(execute, CASES))
    report['passed'] = all(row['passed'] for row in report['cases'])
    assert sha(image) == report['image_sha256'], 'image changed during the run'
    (root/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'{"PASS" if report["passed"] else "FAIL"}: {root / "results.json"}')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
