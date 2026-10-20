"""Harmony with upstream scale, scene and kit recall modules."""
import dataclasses
import runpy
from pathlib import Path

BASE = runpy.run_path(str(Path(__file__).resolve().parent / '../midi-harmony/remix.py'))['REMIX']
REMIX = dataclasses.replace(BASE, name='harmony-scenes',
    doc='Harmony degrees, chords and ACCUM with MIDI Scales, MIDI Scenes and KITS.',
    modules=(*BASE.modules, 'MIDI SCALES', 'MIDI SCENES', 'KITS'))
