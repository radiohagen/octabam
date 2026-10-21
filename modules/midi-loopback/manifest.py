"""Pinned author source; reviewed alongside the matching author commit."""
import dataclasses
from pathlib import Path
import runpy
from remix.schema import Gate

SOURCE = Path(__file__).resolve().parent / 'upstream/modules/midi-loopback/manifest.py'
MODULE = runpy.run_path(str(SOURCE), run_name='remix_manifest_midi_loopback')['MODULE']
# The cross-unit author runtime is linked and checked together. Independent
# Linked.reference links cannot resolve its mutual Part State/Loopback symbols.
MODULE = dataclasses.replace(MODULE, linked=tuple(
    dataclasses.replace(unit,
        include=(lambda modules, remix, source=unit.include: source(modules)))
    if unit.include else unit for unit in MODULE.linked
), gates=(
    Gate('tools/verify/verify_midi_loopback_reference.py', stage='image', venv=True),
    *MODULE.gates,
))

# Detailed verification lives in developer notes, outside the README index.
MODULE = dataclasses.replace(MODULE, proof_note="")

# The standalone author pin refuses Scenes. This integration has its explicit
# producer adapter, but still refuses a composition which forgets to select it.
def producers_include(modules, remix=None):
    if 'MIDI SCENES' in modules and 'MIDI LOOPBACK SCENES' not in modules:
        raise ValueError('MIDI Loopback with MIDI Scenes requires MIDI LOOPBACK SCENES')
    return '.set HAVE_SCENES_BRIDGE,1\n' if 'MIDI LOOPBACK SCENES' in modules else ''

MODULE = dataclasses.replace(MODULE,
    conflicts=tuple(pair for pair in MODULE.conflicts if pair[0] != 'MIDI SCENES'),
    linked=tuple(dataclasses.replace(unit, include=producers_include)
                 if unit.label == 'loopbackproducers' else unit for unit in MODULE.linked))
