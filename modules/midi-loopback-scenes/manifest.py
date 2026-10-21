"""Pinned author adapter for the current upstream MIDI Scenes producers."""
import dataclasses
import hashlib
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'modules/midi-harmony/upstream'
MODULE = runpy.run_path(str(SOURCE / 'modules/midi-loopback-scenes/manifest.py'))['MODULE']

def boundaries(modules, remix=None):
    # Upstream 43a142aa changes the engine-latch follow. The CC and mixer
    # producer spans and scn_state+288/+292 remain unchanged; image gate
    # verifies their linked offsets, actual calls and all routing modes.
    actual = hashlib.sha256((ROOT / 'modules/midi-scenes/scenes.s').read_bytes()).hexdigest()
    if actual != '9f8e2305f8a0bcddf1a1bbcd1aad9bf910e67ef3f875b2b7f7113e97b1759eb7':
        raise ValueError('MIDI Scenes bridge needs a source-boundary audit')
    return ''

MODULE = dataclasses.replace(MODULE, linked=tuple(
    dataclasses.replace(unit, source=str(SOURCE / unit.source), include=boundaries)
    for unit in MODULE.linked))
