"""Pinned author declaration; resolve its native paths from the source checkout."""
import dataclasses
from pathlib import Path
import runpy
from remix.schema import Gate

SOURCE = (Path(__file__).resolve().parent / 'upstream').resolve()
MODULE = runpy.run_path(str(SOURCE / 'modules/midi-harmony/manifest.py'), run_name='author_midi_harmony')['MODULE']
# The author integration owns NOTE SETUP confirmation in Part State. Upstream's
# current Part State omits it, so HARM brings the same source and hook here.
PART = runpy.run_path(str(SOURCE / 'modules/midi-part-state/manifest.py'), run_name='author_harmony_part')['MODULE']
setup = next(unit for unit in PART.linked if unit.label == 'midipartsetup')
setup = dataclasses.replace(setup, include=lambda modules, remix, source=setup.include: source(modules))
MODULE = dataclasses.replace(MODULE,
    linked=(setup, *MODULE.linked),
    detours=tuple(hook for hook in PART.detours if hook.unit == 'midipartsetup') + MODULE.detours)
MODULE = dataclasses.replace(MODULE, linked=tuple(
    dataclasses.replace(unit, source=str(SOURCE / unit.source)) for unit in MODULE.linked
))

MODULE = dataclasses.replace(MODULE, gates=(
    Gate("tools/verify/verify_harmony_reference.py", stage="image", venv=True), *MODULE.gates,
    Gate("tools/verify/verify_harmony_settings.py", stage="image", venv=True),
))
