"""Upstream Bus with the shared personal MIDI selection."""
import dataclasses
import runpy
from pathlib import Path
from remix.schema import Proof

BASE = runpy.run_path(str(Path(__file__).resolve().parent / '../octabam-bus/remix.py'))['REMIX']
MIDI = ('SEQUENCER EVENTS', 'EDIT EVENTS', 'MIDI PART STATE', 'MIDI SRAM',
        'MIDI SCALES', 'MIDI FOLLOW', 'MIDI HARMONY', 'MIDI LOOPBACK',
        'MIDI LOOPBACK SCENES')
REMIX = dataclasses.replace(BASE, name='midi-bus', proof=Proof.PORT,
    proof_note='Personal combination: hardware acceptance pending',
    doc='Upstream Bus with Scales, Follow, HARM and Loopback; shared event dispatch.',
    modules=tuple(dict.fromkeys((*BASE.modules, *MIDI))))
