"""Compatibility selection uses upstream's native MIDI drawing fix."""
from dataclasses import replace
from pathlib import Path
import runpy
from remix.schema import Proof

base = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'midi-scales/remix.py'))['REMIX']
REMIX = replace(base, name='quantizer-midi-drawer',
    modules=tuple(m for m in base.modules if m != 'MIDI SCALES') +
            ('SCALE QUANTIZER', 'QUANTIZER MIDI DRAWER'),
    proof=Proof.CHECK, proof_note='',
    doc='Stock effects with the compatibility name for upstream MIDI chromatic drawing.')
