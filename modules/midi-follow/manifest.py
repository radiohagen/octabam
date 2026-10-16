"""MIDI Follow from the shared, explicitly pinned author source."""
import dataclasses
from pathlib import Path
import runpy
from remix.schema import Gate
SOURCE = Path(__file__).resolve().parent / '../midi-loopback/upstream/modules/midi-follow/manifest.py'
MODULE = runpy.run_path(str(SOURCE), run_name='remix_manifest_midi_follow')['MODULE']
MODULE = dataclasses.replace(MODULE, proof_note='', gates=(
    Gate('tools/verify/verify_midi_follow_reference.py', stage='image', venv=True),
    *MODULE.gates,
))
