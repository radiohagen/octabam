"""Harmony with upstream MIDI scales, routing and kit recall."""
import dataclasses
import runpy
from pathlib import Path
from remix.schema import Proof

BASE = runpy.run_path(str(Path(__file__).resolve().parent / '../midi-harmony/remix.py'))['REMIX']
REMIX = dataclasses.replace(BASE, name='harmony-midi', proof=Proof.PORT,
    doc='Harmony degrees, chords and ACCUM with MIDI Scales, Loopback and KITS.',
    modules=(*BASE.modules, 'MIDI SCALES', 'MIDI LOOPBACK', 'KITS'))
