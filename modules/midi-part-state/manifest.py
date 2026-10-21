"""Pinned author source; reviewed alongside the matching author commit."""
import dataclasses
from pathlib import Path
import runpy
from remix.schema import Gate

SOURCE = Path(__file__).resolve().parent / '../midi-loopback/upstream/modules/midi-part-state/manifest.py'
MODULE = runpy.run_path(str(SOURCE), run_name='remix_manifest_midi_part_state')['MODULE']

# The original copy unit branches directly to SRAM with a signed 16-bit
# displacement. Larger compositions can place the units more than 32 KiB
# apart. Use the author's existing local-branch/absolute-jump correction;
# the remaining Part State units keep their original source and pin.
COPY_SOURCE = (Path(__file__).resolve().parent /
               '../midi-harmony/upstream/modules/midi-part-state/part-copy.s').resolve()
MODULE = dataclasses.replace(MODULE, linked=tuple(
    dataclasses.replace(unit, source=str(COPY_SOURCE))
    if unit.label == 'midipartcopy' else unit for unit in MODULE.linked
))

# Cold-entry unit is independently linkable; enforce its author reference
# on every build. The mutually linked DRAM units use the combined oracle.
MODULE = dataclasses.replace(MODULE, linked=tuple(
    dataclasses.replace(unit, reference=(0x400d6b80,
        'c7a3725b8e7b3ba4f830795b198e6800b2fbf9490bbd52e26e70c88252ec9b88'))
    if unit.label == 'midipartentry' else
    dataclasses.replace(unit, boot_mutable=(('mp_snapshot', 4 * 8 * 36),
                                          ('mp_part_epochs', 64 * 4)))
    if unit.label == 'midipartcopy' else unit for unit in MODULE.linked
))
# The pinned author manifest predates include(modules, remix). Keep its source
# pin unchanged while adapting the existing Part State units to this build ABI.
MODULE = dataclasses.replace(MODULE, linked=tuple(
    dataclasses.replace(unit, include=(lambda modules, remix, source=unit.include: source(modules)))
    if unit.include else unit for unit in MODULE.linked
))

MODULE = dataclasses.replace(MODULE, gates=(
    *MODULE.gates,
    Gate('tools/verify/verify_midi_part_boot.py', stage='image', venv=True),
    Gate('tools/verify/verify_midi_part_activation.py', stage='image', venv=True),
))

# Detailed verification lives in developer notes, outside the README index.
MODULE = dataclasses.replace(MODULE, proof_note="")
