"""Explicitly pinned radiohagen author source."""
import dataclasses
from pathlib import Path
import runpy
from remix.schema import Gate
SOURCE=Path(__file__).resolve().parent/'../midi-loopback/upstream/modules/midi-sram/manifest.py'
MODULE=runpy.run_path(str(SOURCE),run_name='remix_manifest_midi_sram')['MODULE']
