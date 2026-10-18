"""Boot write declarations are owned, bounded, zero-initialized and opt-in."""
import dataclasses
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'tools/verify')]
from remix import platform_build
from remix.schema import Linked
from boot_mutable import compare_runtime, resolve_ranges

TOOLS = all(shutil.which(t) for t in ('m68k-elf-as', 'm68k-elf-ld',
                                     'm68k-elf-objcopy', 'm68k-elf-objdump', 'm68k-elf-nm'))


class DeclarationTests(unittest.TestCase):
    def test_requires_dram_positive_size_unique_name(self):
        for kwargs in ({}, {'loader': True}, {'dram': True, 'loader': True}):
            with self.assertRaises(ValueError):
                Linked('u', 'u.s', boot_mutable=(('state', 4),), **kwargs)
        for declaration in ((('', 4),), (('state', 0),), (('state', -1),),
                            (('state', True),), (('state', 1.5),),
                            (('state', 4), ('state', 8)), (('state',),), (None,)):
            with self.subTest(declaration=declaration), self.assertRaises(ValueError):
                Linked('u', 'u.s', dram=True, boot_mutable=declaration)

    def test_existing_budget_and_payload_length_are_preserved(self):
        raw = bytes(256)
        self.assertEqual(compare_runtime(0, raw, bytes([1])*64+raw[64:], []), (True, 0, 64))
        self.assertEqual(compare_runtime(0, raw, bytes([1])*65+raw[65:], []), (False, 0, 65))
        self.assertEqual(compare_runtime(0, raw, bytes([1])*256, [(0, 192)]), (True, 192, 64))
        self.assertEqual(compare_runtime(0, raw, bytes([1])*256, [(0, 191)]), (False, 191, 65))
        for actual in (raw[:-1], raw+b'\0'):
            self.assertFalse(compare_runtime(0, raw, actual, [(0, 256)])[0])

    def test_no_declarations_need_no_link_metadata(self):
        self.assertEqual(resolve_ranges([], {}, None, b''), [])


@unittest.skipUnless(TOOLS, 'needs the m68k-elf toolchain')
class LinkedDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='boot-mutable-', dir=ROOT/'out')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        # Two units deliberately use the same local symbol name.
        self.units = []
        for i in range(2):
            source = self.work/f'u{i}.s'
            source.write_text('.text\nentry: nop\nstate: .space 80\nalias = state+4\n')
            self.units.append(Linked(f'u{i}', str(source), dram=True,
                                     boot_mutable=(('state', 80),)))
        raw, _, _, self.tables = platform_build.link_runtime(
            [('OWNER', u) for u in self.units], self.work, {}, 0x1000)
        self.raw = raw
        self.layout = {'base': 0x1000, 'units': [['OWNER', u.label, 82, 0] for u in self.units]}

    def resolve(self, units=None, raw=None, layout=None):
        return resolve_ranges([SimpleNamespace(key='OWNER', linked=units or self.units)],
                              layout or self.layout, self.work,
                              self.raw if raw is None else raw)

    def changed(self, declaration):
        return [dataclasses.replace(self.units[0], boot_mutable=declaration), self.units[1]]

    def test_same_named_locals_resolve_to_their_own_objects(self):
        ranges = self.resolve()
        self.assertEqual(ranges, [(self.tables[u.label]['state'],
                                  self.tables[u.label]['state']+80) for u in self.units])
        actual = bytearray(self.raw)
        for start, end in ranges:
            actual[start-0x1000:end-0x1000] = bytes([0xa5])*(end-start)
        self.assertEqual(compare_runtime(0x1000, self.raw, actual, ranges), (True, 160, 0))

    def test_wrong_owner_or_missing_symbol_is_rejected(self):
        for units, layout in ((self.changed((('missing', 4),)), self.layout),
                              (self.units, {'base': 0x1000, 'units': []})):
            with self.assertRaises(ValueError):
                self.resolve(units, layout=layout)

    def test_section_overrun_nonzero_code_and_overlap_are_rejected(self):
        for declaration, message in (((('state', 81),), 'owning section'),
                                     ((('entry', 2),), 'zeroed'),
                                     ((('state', 80), ('alias', 4)), 'overlapping')):
            with self.subTest(declaration=declaration), self.assertRaisesRegex(ValueError, message):
                self.resolve(self.changed(declaration))

    def test_outside_payload_or_nonzero_initial_data_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'runtime payload'):
            self.resolve(raw=self.raw[:-1])
        bad = bytearray(self.raw)
        bad[self.tables['u0']['state']-0x1000] = 1
        with self.assertRaisesRegex(ValueError, 'zeroed'):
            self.resolve(raw=bad)


if __name__ == '__main__':
    unittest.main()
