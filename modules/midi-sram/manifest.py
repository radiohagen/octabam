"""Pinned author declaration; resolve its native paths from the source checkout."""
import dataclasses
from pathlib import Path
import runpy

SOURCE = (Path(__file__).resolve().parent / '../midi-harmony/upstream').resolve()
MODULE = runpy.run_path(str(SOURCE / 'modules/midi-sram/manifest.py'), run_name='author_midi_sram')['MODULE']
MODULE = dataclasses.replace(MODULE, linked=tuple(
    dataclasses.replace(unit, source=str(SOURCE / unit.source)) for unit in MODULE.linked
))
