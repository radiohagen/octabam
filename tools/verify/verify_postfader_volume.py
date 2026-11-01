#!/usr/bin/env python3
"""Source volume and scene XLEV through the real firmware and both DSPs.

Uses the existing owned T2-only FLEX fixture. Scene endpoint bytes are injected
at the same live lock rows as verify_usb_post; CC 48 then drives the stock
crossfader/morph/publisher. The gate does not write the resulting mixer or DSP
gain words. It checks zero excitation, unchanged other-sender gain, preserved
post-burst tails, and AMP VOL / scene XVOL already present in the source audio.

No build or physical-unit timing claim. Run a frozen pre-fix image with
--cases audible,xlev_zero as a negative control: the XLEV zero checks must fail.
"""
import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import wave
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import toolpath  # noqa: E402,F401
import verify_postfader as pf  # noqa: E402

CASES = ('audible', 'xlev_zero', 'other_xlev_zero', 'tail', 'tail_xlev_zero',
         'amp_half', 'amp_zero', 'xvol_zero')
XLV_LOCKS, PARAM_LOCKS = 0x800010d4, 0x80000ed4
PEEKS = '0:Y:e00,32;1:Y:30100,256'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def poke_bytes(address, values):
    return ';'.join(f'{address+i:#x}={v}' for i, v in enumerate(values))


def execute(image, root, tag):
    folder = root / tag
    # Own all live scene endpoints, independent of the template's scenes.
    # Param 17 is AMP XVOL; XLV has a separate two-byte-per-track array.
    locks = bytearray([255] * 512)
    levels = bytearray([127] * 16)
    if tag in ('xlev_zero', 'tail_xlev_zero'):
        levels[3] = 0                       # T2: A=127, B=0
    elif tag == 'other_xlev_zero':
        levels[13] = 0                      # silent T7, other sender unchanged
    elif tag == 'xvol_zero':
        locks[64+2*17:64+2*17+2] = bytes([127, 0])
    setup = ';'.join(('0x80000049=1', poke_bytes(PARAM_LOCKS, locks),
                      poke_bytes(XLV_LOCKS, levels)))
    amp = 64 if tag == 'amp_half' else 0 if tag == 'amp_zero' else 127
    # Every run receives the same messages at the same times. At frame 64
    # the continuous fixtures are still silent (their onset is 200 ms).
    midi = folder / 'volume.midi'
    first_scene = 0 if tag.startswith('tail') else 127
    midi.write_text(f'64 B1 19 {amp:02X}\n64 B1 30 {first_scene:02X}\n1000 B1 30 7F\n')
    command = [str(pf.EMU), '--image', str(image), '--card', str(folder/'card.img'),
               '--set', 'OCTABAM', '--project', 'PF', '--sequencer', '--internal-clock',
               '--frames', str(pf.FRAMES), '--load-ms', '90000', '--dsp',
               '--main-level', '64', '--poke', setup, '--midi', str(midi),
               '--block-dump', str(folder/'blocks.dump'),
               '--mem-dump', f'0x80000000,0x8000={folder/"sram.bin"}',
               '--dsp-peek', PEEKS]
    with (folder/'run.txt').open('w') as log:
        code = subprocess.run(command, cwd=pf.ROOT, stdout=log,
                              stderr=subprocess.STDOUT).returncode
    return tag, code


def slices(packets, core, bases, start, count, direction='<', kind=1):
    return {frame: tuple(words[start:start+count]) for base in bases
            for frame, words in packets.get((direction, kind, core, base), [])
            if frame > pf.WARM}


def rms(rows):
    # Audio read-back is big-endian signed 24-bit audio << 8, split into
    # halfwords by blockdump. Rejoin it before comparing volume, not the
    # unsigned high/low words (which would give a meaningless RMS).
    values = []
    for words in rows.values():
        for i in range(0, len(words), 2):
            value = words[i] << 16 | words[i+1]
            values.append(value - (1 << 32) if value & (1 << 31) else value)
    return math.sqrt(sum(v*v for v in values) / len(values)) if values else 0.0


def wet_rms(words):
    values = [w - (1 << 24) if w & (1 << 23) else w for w in words]
    return math.sqrt(sum(v*v for v in values) / len(values)) if values else 0.0


def inspect(root, tag, code):
    folder = root / tag
    packets = pf.bd.classes(pf.bd.read(folder/'blocks.dump'))
    raw = (folder/'sram.bin').read_bytes()
    mix = int.from_bytes(raw[0x3c10:0x3c14], 'big') - 0x80000000
    u16 = lambda off: int.from_bytes(raw[off:off+2], 'big')
    dry = slices(packets, 1, (0x80003190, 0x80003590), 64, 64)
    sends = slices(packets, 1, (0x80000110, 0x80000310), 44, 2, '>', 0)
    other = slices(packets, 0, (0x80000210, 0x80000410), 76, 2, '>', 0)
    wet = slices(packets, 0, (0x80003390, 0x80003790), 192, 64)
    seen = {}
    for core, space, address, values in re.findall(
            r'core (\d) ([XYP]):(0x[0-9a-f]+): ([0-9a-f ]+)', (folder/'run.txt').read_text()):
        seen[int(core), space, int(address, 16)] = [int(v, 16) for v in values.split()]
    rv, dl = seen.get((0, 'Y', 0xe00), []), seen.get((1, 'Y', 0x30100), [])
    checks = {
        'firmware completed': code == 0,
        'MASTER on and stock OT mute mode': raw[0x34] == 1 and raw[0xdc:0xe0] == bytes(4),
        'both saved scene mute settings are off': raw[6:8] == bytes(2),
        'enough live audio and parameter frames': min(map(len, (dry, sends, other, wet))) > 100,
        'T2 original sends retain participation': bool(sends) and all(d & 0x8000 and r & 0x8000 for d, r in sends.values()),
        'T7 original sends retain participation': bool(other) and all(d & 0x8000 and r & 0x8000 for d, r in other.values()),
        'both wet buffer snapshots complete': len(rv) == 32 and len(dl) == 256,
    }
    if tag in ('xlev_zero', 'tail_xlev_zero'):
        checks.update({
            'scene B XLEV zero reached real mixer snapshot': u16(mix+12) == 0 and u16(mix+10) > 0,
            'both T2 excitation coefficients zero throughout comparison': bool(sends) and all(v == (0x8000, 0x8000) for v in sends.values()),
        })
    if tag == 'other_xlev_zero':
        checks.update({
            'T7 XLEV zero reached real mixer snapshot': u16(mix+52) == 0 and u16(mix+50) > 0,
            'both T7 excitation coefficients zero throughout comparison': bool(other) and all(v == (0x8000, 0x8000) for v in other.values()),
        })
    if tag in ('audible', 'amp_half', 'xlev_zero', 'other_xlev_zero'):
        checks['T2 pre-SEND dry audio is live'] = sum(any(w) for w in dry.values()) > 100
    if tag in ('xlev_zero', 'amp_zero', 'xvol_zero'):
        checks.update({
            'master output silent after warmup': bool(wet) and not any(any(w) for w in wet.values()),
            'reverb wet buffer stays silent': len(rv) == 32 and not any(rv),
            'delay wet buffer stays silent': len(dl) == 256 and not any(dl),
        })
    if tag in ('amp_zero', 'xvol_zero'):
        checks.update({
            'volume already silenced the pre-SEND track audio': bool(dry) and not any(any(w) for w in dry.values()),
            'post-fader send controls remain live': bool(sends) and all(d & 0x7fff and r & 0x7fff for d, r in sends.values()),
        })
    if tag in ('audible', 'amp_half'):
        checks['both wet buffers have positive-control audio'] = any(rv) and any(dl)
    return dict(checks=checks, dry=dry, sends=sends, other=other, wet=wet,
                receipt=dict(name=tag, frames=len(wet), dry_rms=rms(dry), output_rms=rms(wet),
                             t2_main=u16(mix+10), t2_xlev=u16(mix+12), t7_xlev=u16(mix+52),
                             reverb_wet_nonzero_words=sum(bool(w) for w in rv),
                             delay_wet_nonzero_words=sum(bool(w) for w in dl),
                             reverb_wet_rms=wet_rms(rv), delay_wet_rms=wet_rms(dl),
                             blocks_sha256=sha(folder/'blocks.dump'), sram_sha256=sha(folder/'sram.bin')))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('remix', nargs='?', default='test/send-return-poc')
    ap.add_argument('--image', type=Path, default=pf.ROOT/'out/mainos_bus.bin')
    ap.add_argument('--project', type=Path, default=os.environ.get('OT_PROJECT'))
    ap.add_argument('--out', type=Path, default=pf.ROOT/'out/postfadervolume')
    ap.add_argument('--cases', default=','.join(CASES), help='comma-separated subset; default is all eight cases')
    args = ap.parse_args()
    remix = pf.registry.remix(args.remix)
    if not {'POST FADER', 'RETURNS', 'REVERB SERVER', 'DELAY SERVER'}.issubset(remix.modules):
        print('[ -- ] source-volume gate needs POST FADER, RETURNS and both bus engines'); return 0
    if args.project is None or not pf.EMU.is_file():
        print('[SKIP] source-volume gate needs --project/OT_PROJECT and the port'); return 0
    if not args.image.is_file() or not (args.project/'project.work').is_file():
        ap.error('image and local project.work must exist')
    cases = args.cases.split(',')
    if len(set(cases)) != len(cases) or any(c not in CASES for c in cases):
        ap.error('cases must be a unique subset of ' + ','.join(CASES))
    if set(cases) - {'tail', 'tail_xlev_zero'} and 'audible' not in cases:
        ap.error('include audible as the positive control')
    if 'tail_xlev_zero' in cases and 'tail' not in cases:
        ap.error('include tail as the tail-preservation reference')
    pf.OUT = root = args.out.resolve()
    if not root.is_relative_to((pf.ROOT/'out').resolve()):
        ap.error('--out must stay inside this worktree\'s owned out directory')
    generated = root/'source'
    if args.project.resolve().is_relative_to(root):
        ap.error('the structural template must be outside this gate\'s output directory')
    root.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(generated, ignore_errors=True)
    command = [str(pf.PY), str(pf.ROOT/'tools/harness/usb_sig_project.py'),
               '--source', str(args.project.resolve()), '--out', str(generated)]
    subprocess.run(command, cwd=pf.ROOT, check=True, stdout=subprocess.DEVNULL)
    # The structural template may have either scene muted. Own these saved
    # settings just as stage() owns track mutes, so the real morph runs.
    project = generated/'project.work'
    settings = project.read_bytes()
    for side in ('A', 'B'):
        key = f'SCENE_{side}_MUTE'.encode()
        settings, count = re.subn(rb'(?m)^' + key + rb'=\d+', key+b'=0', settings)
        assert count == 1, f'fixture needs the {key.decode()} project setting'
    project.write_bytes(settings)
    image = root/'mainos.bin'
    if args.image.resolve() != image:
        shutil.copy2(args.image, image)
    with wave.open(str(generated/'AUDIO/USBSIG/T2.wav'), 'rb') as source:
        params, samples = source.getparams(), source.readframes(source.getnframes())
    # 200 ms silence gives the real CC receiver and send smoothing time to
    # settle before new excitation. The tail burst starts after 100 ms so
    # both references have already reached scene A, ends at 200 ms, then
    # rings freely across the scene-B move at frame 1000 (~363 ms).
    cutoff = 8820 * params.nchannels * params.sampwidth
    onset = cutoff // 2
    for filename, data in (('late.wav', bytes(cutoff)+samples[cutoff:]),
                           ('burst.wav', bytes(onset)+samples[onset:cutoff]+bytes(len(samples)-cutoff))):
        with wave.open(str(root/filename), 'wb') as output:
            output.setparams(params); output.writeframes(data)
    report = dict(remix=args.remix, image_sha256=sha(image), source_image=str(args.image.resolve()),
                  emulator_sha256=sha(pf.EMU), script_sha256=sha(__file__), helper_sha256=sha(pf.__file__),
                  selected_cases=cases, full_suite=tuple(cases) == CASES,
                  compared_after_frame=pf.WARM, total_frames=pf.FRAMES,
                  limits='Live scene lock rows and real MIDI CC48/morph path; no physical timing, split-ramp or project scene persistence proof')
    for tag in cases:
        track2 = root/('burst.wav' if tag.startswith('tail') else 'late.wav')
        audio = [f'{track2 if t == 2 else generated / "AUDIO/USBSIG" / f"T{t}.wav"}:AUDIO/USBSIG/T{t}.wav'
                 for t in range(1, 9)]
        with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet):
            pf.stage(generated, args.remix, tag, 100, audio)
        print(f'staged {tag}', flush=True)
    with ThreadPoolExecutor(2) as pool:
        codes = dict(pool.map(lambda tag: execute(image, root, tag), cases))
    rows = {tag: inspect(root, tag, codes[tag]) for tag in cases}
    for left, right in (('audible', 'other_xlev_zero'), ('tail', 'tail_xlev_zero')):
        if right in rows:
            a, b = rows[left], rows[right]
            common = a['wet'].keys() & b['wet'].keys()
            rows[right]['checks']['wet return matches reference sample for sample'] = (
                len(common) > 100 and all(a['wet'][f] == b['wet'][f] for f in common))
            rows[right]['checks']['reference wet tail/output is non-silent'] = sum(any(a['wet'][f]) for f in common) > 100
            rows[right]['receipt']['different_output_frames'] = sum(a['wet'][f] != b['wet'][f] for f in common)
    for tag in ('other_xlev_zero', 'amp_half', 'amp_zero', 'xvol_zero'):
        if tag in rows:
            base, row = rows['audible'], rows[tag]
            common = base['sends'].keys() & row['sends'].keys()
            row['checks']['T2 send gain unchanged; no duplicate source volume factor'] = (
                len(common) > 100 and all(base['sends'][f] == row['sends'][f] for f in common))
    if 'xlev_zero' in rows:
        base, row = rows['audible'], rows['xlev_zero']
        common = base['other'].keys() & row['other'].keys()
        row['checks']['T2 scene fade leaves T7 send coefficients unchanged'] = (
            len(common) > 100 and all(base['other'][f] == row['other'][f] for f in common))
    if 'amp_half' in rows:
        a, b = rows['audible']['receipt'], rows['amp_half']['receipt']
        dry_ratio = b['dry_rms'] / a['dry_rms'] if a['dry_rms'] else 0
        wet_ratio = b['output_rms'] / a['output_rms'] if a['output_rms'] else 0
        rv_ratio = b['reverb_wet_rms'] / a['reverb_wet_rms'] if a['reverb_wet_rms'] else 0
        dl_ratio = b['delay_wet_rms'] / a['delay_wet_rms'] if a['delay_wet_rms'] else 0
        rows['amp_half']['checks']['reduced AMP VOL attenuates incoming audio and return'] = 0.01 < dry_ratio < 0.6 and 0.01 < wet_ratio < 0.6
        rows['amp_half']['checks']['both isolated wet buffers reflect reduced source volume'] = 0.01 < rv_ratio < 0.6 and 0.01 < dl_ratio < 0.6
        b.update(dry_rms_ratio=dry_ratio, output_rms_ratio=wet_ratio,
                 reverb_wet_rms_ratio=rv_ratio, delay_wet_rms_ratio=dl_ratio)
    report['cases'] = []
    for tag, row in rows.items():
        checks = row['checks']
        for name, ok in checks.items():
            print(f'  [{"ok" if ok else "FAIL"}] {tag}: {name}', flush=True)
        report['cases'].append(dict(row['receipt'], checks=checks, passed=all(checks.values())))
    report['passed'] = all(c['passed'] for c in report['cases'])
    assert sha(image) == report['image_sha256'], 'image changed during the run'
    (root/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'{"PASS" if report["passed"] else "FAIL"}: {root/"results.json"}')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
