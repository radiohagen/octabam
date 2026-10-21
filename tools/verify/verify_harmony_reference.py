#!/usr/bin/env python3
"""Independently assemble the pinned author's declarations and compare port objects."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import toolpath
from remix import registry


def main():
    remix = registry.remix(sys.argv[1])
    selected = {m.key: m for m in registry.selected(remix)}
    author = ROOT / 'modules/midi-harmony/upstream'
    layout = json.loads((ROOT / 'out/platform/layout.json').read_text())
    positions = {item[1]: i for i, item in enumerate(layout['units'])}
    checked = []
    with tempfile.TemporaryDirectory(prefix='harmony-author-reference-') as tmp:
        work = Path(tmp)
        for slug in ('midi-harmony', 'midi-sram', 'midi-part-state'):
            declaration = runpy.run_path(str(author / 'modules' / slug / 'manifest.py'))['MODULE']
            units = declaration.linked
            if slug == 'midi-part-state':
                units = tuple(u for u in units if u.label == 'midipartcopy')
            if slug == 'midi-harmony':
                part = runpy.run_path(str(author / 'modules/midi-part-state/manifest.py'))['MODULE']
                units = (next(u for u in part.linked if u.label == 'midipartsetup'), *units)
            for unit in units:
                assert unit.dram, unit.label
                folder = work / unit.label
                folder.mkdir()
                args = []
                if unit.include:
                    (folder / 'remix.inc').write_text(unit.include(selected) if unit.label in ('midipartsetup', 'midipartcopy') else unit.include(selected, remix))
                    args = ['-I', str(folder)]
                if unit.label == 'midipartcopy':
                    # Resolve the author's activation cells independently of
                    # the installed runtime. The reference address is only the
                    # author's oracle; other resident modules can move the unit.
                    # Use its installed native-entry detour for the placement,
                    # and independently assembled offsets for the cells.
                    entry = folder / 'entry.o'
                    subprocess.run(['m68k-elf-as', '-mcpu=5407', '-o', str(entry),
                                    str(author / 'modules/midi-part-state/entry.s')], check=True)
                    rows = subprocess.check_output(['m68k-elf-nm', str(entry)], text=True)
                    offsets = {f[2]: int(f[0], 16) for line in rows.splitlines()
                               if len(f := line.split()) == 3 and f[1] != 'U'}
                    image = (ROOT / 'out/mainos_bus.bin').read_bytes()
                    hook = image[0x40020898 - 0x40000400:0x40020898 - 0x40000400 + 6]
                    assert hook[:2] == bytes.fromhex('4ef9'), 'Part State entry detour'
                    base = int.from_bytes(hook[2:], 'big') - offsets['mp_copy_entry']
                    for name, _default in unit.defsyms:
                        args += ['--defsym', f'{name}=0x{base + offsets[name]:x}']
                obj = folder / 'author.o'
                subprocess.run(['m68k-elf-as', '-mcpu=54455', *args, '-I', str(author),
                                '-o', str(obj), str(author / unit.source)], check=True)
                installed = ROOT / 'out/platform/runtime' / f'{positions[unit.label]:02d}_{unit.label}.o'
                assert obj.read_bytes() == installed.read_bytes(), unit.label
                checked.append(unit.label)
    print(f'[ok] {len(checked)} Harmony/Part State/SRAM objects byte-identical to independent author assembly')


if __name__ == '__main__':
    main()
