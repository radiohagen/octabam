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
        for slug in ('midi-harmony', 'midi-sram'):
            declaration = runpy.run_path(str(author / 'modules' / slug / 'manifest.py'))['MODULE']
            units = declaration.linked
            if slug == 'midi-harmony':
                part = runpy.run_path(str(author / 'modules/midi-part-state/manifest.py'))['MODULE']
                units = (next(u for u in part.linked if u.label == 'midipartsetup'), *units)
            for unit in units:
                assert unit.dram and not unit.defsyms, unit.label
                folder = work / unit.label
                folder.mkdir()
                args = []
                if unit.include:
                    (folder / 'remix.inc').write_text(unit.include(selected) if unit.label == 'midipartsetup' else unit.include(selected, remix))
                    args = ['-I', str(folder)]
                obj = folder / 'author.o'
                subprocess.run(['m68k-elf-as', '-mcpu=54455', *args, '-I', str(author),
                                '-o', str(obj), str(author / unit.source)], check=True)
                installed = ROOT / 'out/platform/runtime' / f'{positions[unit.label]:02d}_{unit.label}.o'
                assert obj.read_bytes() == installed.read_bytes(), unit.label
                checked.append(unit.label)
    print(f'[ok] {len(checked)} Harmony/SRAM objects byte-identical to independent author assembly')


if __name__ == '__main__':
    main()
