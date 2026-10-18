"""Translation follow-up on the existing Loopback composition."""
import dataclasses
import runpy
from pathlib import Path
from remix.schema import Proof

BASE=runpy.run_path(str(Path(__file__).resolve().parent/'../midi-loopback/remix.py'))['REMIX']
REMIX=dataclasses.replace(BASE,name='midi-loopback-translation',
    modules=(*BASE.modules,'STORE','MIDI LOOPBACK TRANSLATION'),
    proof=Proof.PORT,proof_note='Development follow-up; no hardware acceptance.',
    doc='Loopback with optional, disabled-by-default per-destination note translation.')
