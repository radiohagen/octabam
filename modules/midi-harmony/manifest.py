"""Explicitly pinned radiohagen author source."""
import dataclasses
from pathlib import Path
import runpy
from remix.schema import Gate
SOURCE=Path(__file__).resolve().parent/'../midi-loopback/upstream/modules/midi-harmony/manifest.py'
MODULE=runpy.run_path(str(SOURCE),run_name='remix_manifest_midi_harmony')['MODULE']
MODULE=dataclasses.replace(MODULE,gates=(Gate('tools/verify/verify_harmony_reference.py',stage='image',venv=True),*MODULE.gates))
