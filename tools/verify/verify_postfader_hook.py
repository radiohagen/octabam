#!/usr/bin/env python3
"""Execute POST FADER through the installed image detour on both record banks.

The stock builder is stubbed only in this micro gate so records can be varied
independently. verify_postfader.py covers the real builder and DSP audio.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import pathlib
import runpy
import tempfile
from types import SimpleNamespace
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import toolpath  # noqa: E402,F401
from remix import registry, stock
from remix.platform_build import UNCACHED
from image_dsp import unpack_payload
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn import m68k_const as reg

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOK, END, BUILDER = 0x4000d0e4, 0x4000d0ea, 0x40004bd4
BASE, STACK, MIX = 0x40000400, 0x40fff000, 0x80006000


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('remix')
    ap.add_argument('--image', type=pathlib.Path, default=ROOT / 'out/mainos_bus.bin')
    ap.add_argument('--receipt', type=pathlib.Path)
    ap.add_argument('--baseline-ref', help='also execute the pre-XLV hook from this commit in private scratch for an instruction-count comparison')
    args = ap.parse_args()
    remix = registry.remix(args.remix)
    if 'POST FADER' not in remix.modules:
        print('[ -- ] no POST FADER'); return
    mods = registry.bound(remix)
    selected = {mods[k].menu.fx2_id for k in ('SEND', 'DELAY SERVER', 'REVERB SERVER') if k in remix.modules}
    send = mods['SEND'].menu.fx2_id
    delay = mods['DELAY SERVER'].menu.fx2_id if 'DELAY SERVER' in remix.modules else None
    verb = mods['REVERB SERVER'].menu.fx2_id if 'REVERB SERVER' in remix.modules else None
    if remix.fallback == 'SEND': selected.add(0)
    image = args.image.read_bytes()
    elf = ROOT / 'out/platform/runtime/runtime.elf'
    layout_path = ROOT / 'out/platform/layout.json'
    symbols = subprocess.check_output(['m68k-elf-nm', str(elf)], text=True)
    sym = {f[2]: int(f[0], 16) for line in symbols.splitlines()
           if len(f := line.split()) == 3}
    target = sym['pf_frame']
    assert image[HOOK-BASE:END-BASE] == b'\x4e\xb9' + target.to_bytes(4, 'big')
    layout = json.loads(layout_path.read_text())
    # The loader writes through the uncached alias; code executes at base.
    runtime = unpack_payload(image, layout['base'] + UNCACHED)
    assert layout['base'] <= target < layout['base'] + len(runtime), 'hook is outside image runtime'
    assert layout['runtime_end'] == layout['base'] + len(runtime), 'runtime layout does not match image'
    u = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    u.ctl_set_cpu_model(reg.UC_CPU_M68K_CFV4E)
    u.mem_map(0x40000000, 0x1000000); u.mem_map(0x80000000, 0x10000)
    u.mem_write(BASE, image)
    u.mem_write(layout['base'], runtime)
    curve, coefficients = stock_curve()
    table_at = sym['pf_xlv'] - layout['base']
    assert runtime[table_at:table_at + 512] == b''.join(x.to_bytes(2, 'big') for x in coefficients), 'installed XLV table differs from the stock-derived oracle'
    installed = exercise(u, send, delay, verb, selected, coefficients, 'installed hook')
    profiles = instruction_profiles(u, send, delay, verb, selected, coefficients)
    curve_error = control_error_bound(curve, coefficients)
    synthetic = synthetic_ids(coefficients)
    baseline = None
    if args.baseline_ref:
        revision = subprocess.check_output(['git', 'rev-parse', '--verify', args.baseline_ref + '^{commit}'], cwd=ROOT, text=True).strip()
        source = subprocess.check_output(['git', 'show', revision + ':modules/post-fader/postfader.s'], cwd=ROOT)
        ids = {k: mods[k].menu.fx2_id for k in ('SEND', 'DELAY SERVER', 'REVERB SERVER') if k in remix.modules}
        with compiled_hook(ids, remix.fallback, source) as old:
            old_result = exercise(old, send, delay, verb, selected, coefficients, 'pre-XLV baseline hook', scene_aware=False)
            old_profiles = instruction_profiles(old, send, delay, verb, selected, coefficients, scene_aware=False)
        deltas = [new - old for new, old in zip(installed['counts'], old_result['counts'], strict=True)]
        baseline = dict(revision=revision, source_sha256=hashlib.sha256(source).hexdigest(),
                        cases=old_result['cases'], instructions=instruction_summary(old_result['counts']),
                        additional_instructions=instruction_summary(deltas),
                        instruction_profiles=old_profiles,
                        profile_deltas={name: profiles[name] - old_profiles[name] for name in profiles})
        print('[ok] ColdFire hook instruction delta: ' + json.dumps(baseline['additional_instructions'], sort_keys=True))
    receipt = dict(image=str(args.image.resolve()), image_sha256=hashlib.sha256(image).hexdigest(),
                   runtime_base=layout['base'], runtime_bytes=len(runtime),
                   runtime_sha256=hashlib.sha256(runtime).hexdigest(), hook_target=target,
                   layout_sha256=hashlib.sha256(layout_path.read_bytes()).hexdigest(),
                   symbols_elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),
                   installed_cases=installed['cases'], synthetic_cases=sum(r['cases'] for r in synthetic),
                   gate_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
                   xlv_table_sha256=hashlib.sha256(b''.join(x.to_bytes(3, 'big') for x in curve)).hexdigest(),
                   xlv_q15_max_abs_error=max(abs(coefficients[i] / 32768 - min(1, curve[i] / curve[254])) for i in range(256)),
                   installed_instructions=instruction_summary(installed['counts']),
                   instruction_profiles=profiles, control_quantization=curve_error,
                   instruction_scope='Executed ColdFire instructions through the installed detour with a one-instruction stock-builder stub; not CPU cycles or hardware DSP load',
                   baseline=baseline, passed=True)
    print('[ok] image-bound runtime: ' + receipt['runtime_sha256'])
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')


def stock_curve():
    """Independent oracle: read the stock DSP words, not the linked hook table.

    This intentionally does not call the production manifest's table generator.
    Index 254 is the unlocked snapshot word 0x7f00. A normalized Q15 lookup
    preserves the previous LEVEL law there, with nearest-integer rounding and
    unity clamping for the unused index 255.
    """
    sys.path.insert(0, str(ROOT / 'tools/build'))
    import dsp_modmap
    image = stock.STOCK_IMAGE.read_bytes()
    tag, va, length = dsp_modmap.PAYLOADS[0]
    assert tag == 'A'
    modules, blob = dsp_modmap.modules(image, va, length)
    for space, addr, count, data in modules:
        if space == 1 and addr <= 0x6c00 and 0x6d00 <= addr + count:
            offset = data + (0x6c00 - addr) * 3
            curve = [dsp_modmap.w24(blob, offset + 3 * i) for i in range(256)]
            break
    else:
        raise AssertionError('stock payload A does not contain the XLV curve')
    assert curve[0] == 0 and all(a < b for a, b in zip(curve, curve[1:]))
    coefficients = [min(32768, (2 * v * 32768 + curve[254]) // (2 * curve[254])) for v in curve]
    assert coefficients[0] == 0 and coefficients[254] == coefficients[255] == 32768
    assert all(abs(2 * coefficients[i] * curve[254] - 2 * curve[i] * 32768) <= curve[254]
               for i in range(255)), 'normalized XLV error exceeds half a Q15 step'
    return curve, coefficients


def control_error_bound(curve, coefficients):
    """Compare quantized scaling with exact stock ratios over the reachable range.

    LEVEL 127 and a 15-bit maximum control produce at most 32257. Include
    every smaller integer, so this bounds every possible transient control,
    not just the representative control values in the executable hook gate.
    """
    maximum = 32767 * 127 * 127 // 16384
    error = 0
    for index in range(255):
        q, exact_numerator = coefficients[index], curve[index]
        for value in range(maximum + 1):
            error = max(error, abs(((value * q) >> 15) - value * exact_numerator // curve[254]))
    assert error <= 1, 'XLV quantization exceeds one transient control LSB'
    result = dict(curve_indices=255, scaled_controls=maximum + 1,
                  pairs=255 * (maximum + 1), maximum_absolute_control_lsb=error)
    print('[ok] normalized stock curve control error: ' + json.dumps(result, sort_keys=True))
    return result


def instruction_profiles(u, send, delay, verb, selected, coefficients, scene_aware=True):
    """Directly execute the zero-, seven-, and eight-consumer frame costs."""
    untouched = next(i for i in range(64) if i not in selected)
    profiles = {}
    for consumers in (0, 7, 8):
        for scene, word in (('unlocked', 0x7f00), ('half', 0x4000), ('zero', 0)):
            if consumers == 0 and scene != 'unlocked':
                continue
            name = f'{consumers}_consumers_{scene}'
            result = exercise(u, send, delay, verb, selected, coefficients,
                              'instruction profile ' + name, scene_aware=scene_aware,
                              case_vectors=[(name, 0, 2, 127, [word] * 8)],
                              effects=[send] * consumers + [untouched] * (8 - consumers), quiet=True)
            profiles[name] = result['counts'][0]
    print('[ok] ' + ('new' if scene_aware else 'baseline') + ' hook instruction profiles: ' + json.dumps(profiles, sort_keys=True))
    return profiles


def instruction_summary(counts):
    return dict(min=min(counts), max=max(counts), mean=sum(counts) / len(counts),
                histogram={str(k): v for k, v in sorted(Counter(counts).items())})


def cases():
    # Keep the original exhaustive LEVEL/control cases at unlocked XLV: this
    # is also a direct regression check of the previous default behavior.
    for ping in (0, 1):
        for variation in range(8):
            for level in range(128):
                yield 'unlocked', ping, variation, level, [0x7f00] * 8
    # Every lookup index, including half-step scene positions; vary the low
    # seven bits to prove that only XLV >> 7 selects the stock curve entry.
    for ping in (0, 1):
        for variation in range(4):
            for index in range(256):
                words = [(((index + 31 * t) % 256) << 7) | ((variation * 43 + t * 17) & 127)
                         for t in range(8)]
                yield 'scene-sweep', ping, variation, (index * 13 + variation * 29) % 128, words
    # Fade just one source; each companion track keeps the very same snapshot,
    # controls and membership. Endpoint words exercise XLEV zero and full.
    for ping in (0, 1):
        for track in range(8):
            for word in (0, 1, 127, 128, 129, 255, 0x3fff, 0x4000, 0x7eff, 0x7f00, 0x7fff,
                         0x8000, 0x8080, 0xff00, 0xffff):
                words = [0x7f00] * 8
                words[track] = word
                yield 'one-source-scene', ping, track, 127, words


def exercise(u, send, delay, verb, selected, coefficients, label, scene_aware=True,
             case_vectors=None, effects=None, quiet=False):
    untouched = next(i for i in range(64) if i not in selected)
    u.mem_write(BUILDER, bytes.fromhex('4e75'))
    count = 0
    def on_code(cpu, pc, size, data):
        nonlocal count
        if pc == END:
            cpu.emu_stop()
        else:
            count += 1
    hook = u.hook_add(UC_HOOK_CODE, on_code)
    u.mem_write(0x80003c10, MIX.to_bytes(4, 'big'))
    registers = [getattr(reg, 'UC_M68K_REG_' + kind + str(n)) for kind in ('D', 'A') for n in range(8)]
    counts = []
    if effects is None:
        effects = (0, send, delay if delay is not None else 6, verb if verb is not None else 7,
                   untouched, 0x14, send, delay if delay is not None else 6)
    for family, ping, variation, level, xlv_words in cases() if case_vectors is None else case_vectors:
        records = bytearray(b'\xa5' * 1024)
        expected = bytearray(records)
        gains = bytearray(b'\x3c' * 64)
        for t, effect in enumerate(effects):
            off = ping * 512 + t * 64
            # Distinct knobs and dirty low bytes; low byte 60 is a held
            # TEMPO SYNC note for the delay, a fraction everywhere else.
            # Include no send, fraction-only, maximum, note-only and
            # a stale marker; original controls always mask to 15 bits.
            values = (0, 1, 0xff, 0x100, 0x7fff, 0x803c, 0xffff,
                      ((17*t + 63) % 128 << 8) | 0xfe)
            v0, v1 = values[(variation+t) % 8], values[(variation+t+3) % 8]
            for at, value in ((24, v0), (26, v1), (56, effect)):
                records[off+at:off+at+2] = value.to_bytes(2, 'big')
            l = (level + t * 17) % 128
            # Low MAIN bits are deliberately dirty: the existing source send
            # law uses its high byte. Do not silently change that law when
            # adding the independent scene gain, or square XLV a second time.
            main_word = (l << 8) | ((variation * 37 + t * 13) & 255)
            gains[t*8+2:t*8+4] = main_word.to_bytes(2, 'big')
            gains[t*8+4:t*8+6] = xlv_words[t].to_bytes(2, 'big')
        expected[:] = records
        for t in range(8):
            off = ping * 512 + t * 64
            effect = int.from_bytes(records[off+56:off+58], 'big')
            if effect not in selected: continue
            l = gains[t*8+2]
            coefficient = coefficients[(xlv_words[t] >> 7) & 255] if scene_aware else 32768
            def scale(v):
                return ((v * l*l // 16384) * coefficient) // 32768
            for at in (24, 26):
                v = int.from_bytes(records[off+at:off+at+2], 'big') & 0x7fff
                out = scale(v)
                if effect == delay and at == 26:
                    out = (scale(v & 0x7f00) & 0x7f00) | (v & 0xff)
                    participates = bool(v & 0x7f00)
                else:
                    participates = bool(v)
                out |= 0x8000 if participates else 0
                expected[off+at:off+at+2] = out.to_bytes(2, 'big')
        u.mem_write(0x80000110, bytes(records)); u.mem_write(MIX, bytes(gains))
        u.mem_write(0x800000e0, ping.to_bytes(4, 'big'))
        u.reg_write(reg.UC_M68K_REG_SR, 0x2000)
        before = {r: 0x12340000+i for i, r in enumerate(registers)}
        before[reg.UC_M68K_REG_A7] = STACK
        for r, v in before.items(): u.reg_write(r, v)
        count = 0
        u.emu_start(HOOK, 0, count=3000)
        case = (family, ping, level, variation, xlv_words)
        assert u.reg_read(reg.UC_M68K_REG_PC) == END, case
        got = bytes(u.mem_read(0x80000110, 1024))
        assert got == bytes(expected), (case, next((i, a, b) for i, (a, b) in enumerate(zip(got, expected)) if a != b))
        assert bytes(u.mem_read(MIX, 64)) == bytes(gains), (case, 'mixer snapshot')
        assert all(u.reg_read(r) == v for r, v in before.items()), (case, 'registers')
        counts.append(count)
    u.hook_del(hook)
    if not quiet:
        print(f'[ok] {label}: {len(counts)} cases: both banks, every LEVEL and XLV lookup index, scene endpoints, original participation, fractions, held notes, bound IDs, non-send records and registers')
    return dict(cases=len(counts), counts=counts)


@contextmanager
def compiled_hook(ids, fallback, source=None):
    """Assemble in private scratch; never overwrite the current image/layout."""
    inc = runpy.run_path(str(ROOT / 'modules/post-fader/manifest.py'))['ids_inc']
    modules = {key: SimpleNamespace(menu=SimpleNamespace(fx2_id=value)) for key, value in ids.items()}
    with tempfile.TemporaryDirectory(prefix='postfader-ids-') as tmp:
        d = pathlib.Path(tmp)
        (d / 'remix.inc').write_text(inc(modules, SimpleNamespace(fallback=fallback)))
        (d / 'hook.s').write_bytes(source if source is not None else (ROOT / 'modules/post-fader/postfader.s').read_bytes())
        commands = (
            ['m68k-elf-as', '-mcpu=54455', '-I', str(d), '-o', str(d / 'hook.o'), str(d / 'hook.s')],
            ['m68k-elf-ld', '-Ttext=0x40200000', '-e', 'pf_frame', '-o', str(d / 'hook.elf'), str(d / 'hook.o')],
            ['m68k-elf-objcopy', '-O', 'binary', str(d / 'hook.elf'), str(d / 'hook.bin')],
        )
        for cmd in commands:
            subprocess.run(cmd, check=True, capture_output=True)
        u = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        u.ctl_set_cpu_model(reg.UC_CPU_M68K_CFV4E)
        u.mem_map(0x40000000, 0x1000000); u.mem_map(0x80000000, 0x10000)
        u.mem_write(0x40200000, (d / 'hook.bin').read_bytes())
        u.mem_write(HOOK, bytes.fromhex('4eb940200000'))
        yield u


def synthetic_ids(coefficients):
    """Compile only the hook in private scratch: remapped IDs and absent engines.

    This proves the ColdFire selection contract, not a complete 64-ID firmware.
    It never overwrites shared out/ build products.
    """
    results = []
    for ids, fallback in (({'SEND': 33, 'DELAY SERVER': 34, 'REVERB SERVER': 35}, 'SEND'),
                          ({'SEND': 39}, 'NONE')):
        with compiled_hook(ids, fallback) as u:
            selected = set(ids.values()) | ({0} if fallback == 'SEND' else set())
            results.append(exercise(u, ids['SEND'], ids.get('DELAY SERVER'), ids.get('REVERB SERVER'), selected,
                                    coefficients, f'synthetic bound IDs {ids}, fallback {fallback}'))
    return results


if __name__ == '__main__': main()
