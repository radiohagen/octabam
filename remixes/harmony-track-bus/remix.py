"""Experimental Harmony track-local retention with upstream PLOCKS storage."""
from dataclasses import replace
from pathlib import Path
import runpy
from remix.schema import Proof
base = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'octabam-bus/remix.py'))['REMIX']
REMIX = replace(base, name='harmony-track-bus',
    modules=base.modules + ('MIDI PART STATE', 'MIDI SRAM', 'MIDI SCALES',
        'MIDI FOLLOW', 'MIDI HARMONY', 'HARMONY PLOCKS', 'MIDI LOOPBACK',
        'MIDI LOOPBACK SCENES', 'PIO WRITE FIX', 'QUANTIZER MIDI DRAWER'),
    proof=Proof.CHECK, proof_note='',
    doc='Bus with Scales, Follow, Harmony and Loopback; Harmony retained per MIDI step; upstream PLOCKS.')
