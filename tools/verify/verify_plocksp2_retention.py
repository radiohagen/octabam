#!/usr/bin/env python3
"""Execute the actual ColdFire retention codec and legacy writer in Unicorn.

No stock image or project needed. Test old/new snapshots, the proven capacity
bound, invalid input, interruption, SRAM write bounds, and the wrapper ABI.
"""
import pathlib
import random
import struct
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
for path in ('tools', 'tools/emu'):
    sys.path.insert(0, str(ROOT / path))
import toolpath  # noqa: E402,F401
import emu_bringup  # noqa: E402,F401 (select the repository's Unicorn)
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_MEM_WRITE, UC_HOOK_CODE  # noqa: E402
from unicorn import m68k_const as K  # noqa: E402

SLOTS, OLD_BYTES, SIZE = 98304, 30720, 15464
MAX = (OLD_BYTES - 16) // 3
NV, BASE, STOP, STACK = 0x100f8600, 0x200000, 0x10000, 0x30000
REGS = [getattr(K, f'UC_M68K_REG_{r}{i}') for r, n in [('D', 8), ('A', 7)] for i in range(n)]


def build(td, legacy=False):
    sources = (['tools/verify/fixtures/plocks_p2_nv_v1.s'] if legacy else
               ['modules/plocks-p2/p2locks.s', 'modules/plocks-p2/retention.s'])
    objects = []
    for i, source in enumerate(sources):
        obj = td / f'{i}.o'
        subprocess.run(['m68k-elf-as', '-mcpu=54455', '-o', str(obj), str(ROOT / source)], check=True)
        objects.append(str(obj))
    elf, binary = td / 'test.elf', td / 'test.bin'
    subprocess.run(['m68k-elf-ld', f'-Ttext={BASE:#x}', '-e', hex(BASE), '-o', str(elf), *objects], check=True)
    subprocess.run(['m68k-elf-objcopy', '-O', 'binary', str(elf), str(binary)], check=True)
    nm = subprocess.check_output(['m68k-elf-nm', str(elf)], text=True)
    symbols = {f[2]: int(f[0], 16) for f in (line.split() for line in nm.splitlines()) if len(f) == 3}
    return binary.read_bytes(), symbols


class Machine:
    def __init__(self, image, symbols):
        self.s = symbols
        self.uc = u = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        u.ctl_set_cpu_model(K.UC_CPU_M68K_CFV4E)
        u.mem_map(BASE, 0x400000)
        u.mem_write(BASE, image)
        u.mem_map(0x10000000, 0x100000)
        u.mem_map(STOP, STACK)
        u.reg_write(K.UC_M68K_REG_SR, 0x2700)
        self.writes = []
        self.cut = None
        u.hook_add(UC_HOOK_MEM_WRITE, self.write, begin=NV, end=NV + OLD_BYTES - 1)

    def write(self, u, access, address, size, value, data):
        self.writes.append((address, size, value))
        if self.cut == len(self.writes):
            u.emu_stop()

    def call(self, name, bank=3, args=(), interrupted=False, stack=STACK):
        u = self.uc
        initial_sr = u.reg_read(K.UC_M68K_REG_SR) & 0xff00
        initial = [0x123400 + i for i in range(15)]
        initial[0] = bank
        for r, v in zip(REGS, initial):
            u.reg_write(r, v)
        sp = stack - 4 * (len(args) + 1)
        u.mem_write(sp, struct.pack('>' + 'I' * (len(args) + 1), STOP, *args))
        u.reg_write(K.UC_M68K_REG_A7, sp)
        self.writes = []
        u.emu_start(self.s[name], STOP, count=20_000_000)
        if interrupted:
            return
        assert u.reg_read(K.UC_M68K_REG_PC) == STOP, f'{name} did not return'
        assert u.reg_read(K.UC_M68K_REG_A7) == sp + 4, f'{name} stack imbalance'
        if name == 'nv_save':
            assert u.reg_read(K.UC_M68K_REG_SR) & 0xff00 == initial_sr, 'interrupt mask changed'
        if name in ('nv_save', 'nv_apply'):
            start = 0 if name == 'nv_save' else 1
            assert [u.reg_read(r) for r in REGS[start:]] == initial[start:], f'{name} clobbered registers'
        return u.reg_read(K.UC_M68K_REG_D0)

    def table(self, data, bank=3):
        self.uc.mem_write(self.s['STORE'] + bank * SLOTS, bytes(data))

    def read_table(self, bank=3):
        return bytes(self.uc.mem_read(self.s['STORE'] + bank * SLOTS, SLOTS))

    def snapshot(self):
        return bytes(self.uc.mem_read(NV, OLD_BYTES))


def raw(records, bank=3):
    entries = [(i << 7) | v for i, v in records]
    return struct.pack('>4sIII', b'P2NV', bank, len(entries), sum(entries) & 0xffffffff) + b''.join(
        e.to_bytes(3, 'big') for e in entries)


def rice(records, bank=3):
    prev, fields = -1, []
    for i, v in records:
        gap = i - prev - 1
        fields.append('1' * (gap >> 3) + '0' + f'{gap & 7:03b}{v:07b}')
        prev = i
    bits = ''.join(fields)
    bits += '0' * (-len(bits) % 8)
    return struct.pack('>4sIII', b'P2R1', bank, len(records),
                       sum((i << 7) | v for i, v in records) & 0xffffffff) + bytes(
                           int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))


def main():
    subprocess.run([sys.executable, str(ROOT / 'modules/plocks-p2/generate_retention.py'), '--check'], check=True)
    from remix import registry, ledger
    from remix.schema import Claims, Kind, Module
    from dataclasses import replace
    modules = registry.modules()
    claim = modules['PLOCKS P2'].claims.sram
    assert claim == ((NV, SIZE, 'P2NV/P2R1 compact bank copy in CS1'),)
    tail = Module(name='retention-tail-test', key='RETENTION TAIL TEST', kind=Kind.CF_PATCH,
                  doc='Synthetic owner of the released SRAM tail.',
                  claims=Claims(sram=((NV + SIZE, OLD_BYTES - SIZE, 'tail'),)))
    selected = [modules['PLOCKS P2'], modules['SCENES P2']]
    assert not ledger.check([*selected, tail])
    overlap = replace(tail, claims=Claims(sram=((NV + SIZE - 1, 1, 'overlap'),)))
    assert any('SRAM' in problem for problem in ledger.check([*selected, overlap]))
    print('  [ok] ledger frees exactly 15256 SRAM bytes and rejects a one-byte overlap')
    rng = random.Random(90210)
    with tempfile.TemporaryDirectory(prefix='plocks_retention_') as tmp:
        td = pathlib.Path(tmp)
        built = build(td)
        m = Machine(*built)
        old = Machine(*build(td, legacy=True))
        cases = 0
        datasets = []
        for n in (0, 1, 2, 10, 100, 1000, MAX - 1, MAX):
            for shape in ('head', 'tail', 'spread', 'random'):
                indices = (list(range(n)) if shape == 'head' else list(range(SLOTS - n, SLOTS))
                           if shape == 'tail' else [i * SLOTS // n for i in range(n)]
                           if shape == 'spread' else sorted(rng.sample(range(SLOTS), n)))
                datasets.append([(i, rng.randrange(128)) for i in indices])
        # Attain the mathematical maximum: every gap divisible by 8,
        # sum gaps = 8*floor((SLOTS-MAX)/8).
        gaps = [8] * MAX
        gaps[0] += 8 * ((SLOTS - MAX) // 8 - MAX)
        index, worst = -1, []
        for gap in gaps:
            index += gap + 1
            worst.append((index, index & 127))
        assert len(rice(worst)) == SIZE
        datasets += [[(i, i % 128) for i in range(128)], worst]
        for records in datasets:
            table = bytearray(b'\xff' * SLOTS)
            for i, v in records:
                table[i] = v
            a, b = raw(records), rice(records)
            expected = b if len(b) < len(a) else a
            assert len(expected) <= SIZE
            # Actual pre-change machine code, not a model of its writer.
            old.table(table)
            old.call('nv_save')
            legacy = old.snapshot()
            assert legacy[:len(a)] == a
            m.uc.mem_write(NV, legacy)
            m.table(b'\x42' * SLOTS)
            assert m.call('nv_apply') == 1
            assert m.read_table() == table
            # Migration has compacted CS1 before returning to other modules.
            migrated = m.snapshot()
            assert migrated[:len(expected)] == expected
            assert migrated[SIZE:] == legacy[SIZE:]
            m.uc.mem_write(NV, b'\xa5' * OLD_BYTES)
            m.call('nv_save')
            snapshot = m.snapshot()
            assert snapshot[:len(expected)] == expected
            assert snapshot[len(expected):] == b'\xa5' * (OLD_BYTES - len(expected))
            assert m.writes[0] == (NV, 4, 0)
            assert m.writes[-1] == (NV, 4, int.from_bytes(expected[:4], 'big'))
            assert all(NV <= at and at + size <= NV + SIZE for at, size, _ in m.writes)
            m.table(b'\x42' * SLOTS)
            assert m.call('nv_apply') == 1
            assert m.read_table() == table
            cases += 1
        print(f'  [ok] {cases} old-writer upgrade and new-codec round trips, ABI, write bounds; maximum {SIZE} bytes')

        # A distinct owner can overwrite the released tail after legacy
        # restoration. Future saves/loads must remain independent of it.
        m.uc.mem_write(NV + SIZE, b"\x5a" * (OLD_BYTES - SIZE))
        m.table(b"\x42" * SLOTS)
        assert m.call('nv_apply') == 1 and m.read_table() == table
        m.call('nv_save')
        assert m.snapshot()[SIZE:] == b"\x5a" * (OLD_BYTES - SIZE)
        print('  [ok] released SRAM tail can be reused after migration')

        # Every bank including first/last: wrapper bank calculation and isolation.
        for bank in range(16):
            table = bytearray(b'\xff' * SLOTS); table[-1] = bank
            m.table(table, bank); m.call('nv_save', bank)
            m.table(b'\x42' * SLOTS, bank)
            assert m.call('nv_apply', bank) == 1 and m.read_table(bank) == table
        print('  [ok] all 16 bank wrappers')

        sentinel = b'\x42' * SLOTS
        def reject(blob, available=OLD_BYTES, bank=3):
            m.uc.mem_write(NV, bytes(blob) + b'\xa5' * (OLD_BYTES - len(blob)))
            m.table(sentinel)
            result = m.call('plk_nv_decode', args=(m.s['STORE'] + 3 * SLOTS, NV, bank, available))
            assert result == 0, f'accepted bad snapshot {blob[:16].hex()}, available={available}'
            assert m.read_table() == sentinel

        bad = 0
        for encoder in (raw, rice):
            blob = encoder([(0, 0), (8, 127), (SLOTS - 1, 63)])
            lengths = sorted(set(range(min(40, len(blob)))) |
                             {len(blob) - 1, len(blob) // 2, len(blob) - 2})
            for length in lengths:
                reject(blob[:length], length); bad += 1
            for offset in (0, 4, 8, 12, 16, len(blob) - 1):
                corrupt = bytearray(blob); corrupt[offset] ^= 0x80
                reject(corrupt); bad += 1
            reject(blob, bank=2); bad += 1
        for records in ([(SLOTS, 1)], [(0, 1), (0, 2)], [(2, 3), (1, 4)]):
            reject(raw(records)); bad += 1
        reject(struct.pack('>4sIII', b'P2R1', 3, MAX + 1, 0)); bad += 1
        reject(struct.pack('>4sIII', b'P2R1', 3, 1, 0) + b'\xff' * (SIZE - 16)); bad += 1
        padded = bytearray(rice([(0, 1)])); padded[-1] |= 1
        reject(padded); bad += 1
        print(f'  [ok] {bad} truncated/corrupt/wrong-bank snapshots rejected without changing STORE')

        for n, value in ((MAX + 1, 1), (1, 128), (1, 254)):
            table = bytearray(b'\xff' * SLOTS); table[:n] = bytes([value]) * n
            m.table(table); m.call('nv_save')
            assert m.snapshot()[:4] == bytes(4)
            assert all(at + size <= NV + SIZE for at, size, _ in m.writes)
        print('  [ok] overflow and invalid values invalidate the snapshot')

        # Interrupt every SRAM store of a small compressed snapshot. The
        # final magic store is the sole publication point.
        table = bytearray(b'\xff' * SLOTS); table[:16] = bytes(range(16))
        m.table(table); m.call('nv_save'); writes = len(m.writes)
        for cut in range(1, writes):
            m.uc.mem_write(NV, raw([(9, 100)]))
            m.uc.mem_write(m.s['NVBUSY'], bytes(4))
            m.cut = cut; m.call('nv_save', interrupted=True); m.cut = None
            assert m.snapshot()[:4] == bytes(4)
            m.table(sentinel)
            assert m.call('nv_apply') == 0 and m.read_table() == sentinel
            m.table(table)
        print(f'  [ok] interruption at all {writes - 1} pre-publication SRAM stores')

        # Capture every executed instruction address with interrupts enabled.
        # Inject a nested request at representative PCs throughout both scans,
        # header/payload writes and the return from the codec, using a separate
        # task stack and restoring the interrupted CPU context on resume.
        m = Machine(*built)
        m.uc.reg_write(K.UC_M68K_REG_SR, 0x2000)
        m.table(table)
        pcs = []
        def trace(u, pc, size, data):
            if pc >= m.s['plk_nv_encode'] and u.reg_read(K.UC_M68K_REG_SR) & 0x700 == 0:
                if pc not in seen:
                    seen.add(pc); pcs.append(pc)
        seen = set()
        hook = m.uc.hook_add(UC_HOOK_CODE, trace)
        m.call('nv_save')
        m.uc.hook_del(hook)
        assert pcs, 'preemption trace must execute unmasked codec instructions'
        points = pcs[::max(1, len(pcs) // 24)]
        # Sample the executed codec instructions across both passes.
        nested_cases = 0
        for pc in points:
            for new_bank in (3, 15):
                m = Machine(*built)
                m.uc.mem_write(m.s['NVBUSY'], bytes(4))
                m.table(table)
                latest = bytearray(b'\xff' * SLOTS); latest[-1] = 127
                if nested_cases % 3 == 1:
                    latest[:MAX] = bytes(i & 127 for i in range(MAX))
                    latest[-1] = 255
                elif nested_cases % 3 == 2:
                    latest[:MAX + 1] = bytes(i & 127 for i in range(MAX + 1))
                m.uc.reg_write(K.UC_M68K_REG_SR, 0x2000)
                def stop(u, address, size, data):
                    if address == pc and u.reg_read(K.UC_M68K_REG_SR) & 0x700 == 0:
                        u.emu_stop()
                hook = m.uc.hook_add(UC_HOOK_CODE, stop)
                m.call('nv_save', interrupted=True)
                m.uc.hook_del(hook)
                assert m.uc.reg_read(K.UC_M68K_REG_PC) == pc
                context = m.uc.context_save()
                m.table(latest, new_bank)
                m.call('nv_save', new_bank, stack=STACK - 0x4000)
                m.uc.context_restore(context)
                m.uc.emu_start(pc, STOP, count=20_000_000)
                assert m.uc.reg_read(K.UC_M68K_REG_PC) == STOP
                assert m.uc.reg_read(K.UC_M68K_REG_A7) == STACK
                m.table(sentinel, new_bank)
                assert all(at + size <= NV + SIZE for at, size, _ in m.writes)
                restored = m.call('nv_apply', new_bank)
                if nested_cases % 3 == 2:
                    assert restored == 0 and m.read_table(new_bank) == sentinel
                else:
                    assert restored == 1 and m.read_table(new_bank) == latest
                assert m.uc.mem_read(m.s['NVBUSY'], 4) == bytes(4)
                nested_cases += 1
        print(f'  [ok] {nested_cases} UI/engine preemptions: latest same/different bank, density change and overflow')
    print('verify_plocksp2_retention: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
