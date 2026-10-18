"""Optional final-note mapping; native Loopback routing storage stays unchanged."""
from pathlib import Path
from remix.schema import Category, Gate, Kind, Linked, Module, Proof

SOURCE=Path(__file__).resolve().parent/'../midi-loopback/upstream/modules/midi-loopback'
MODULE=Module(
    name='midi-loopback-translation', key='MIDI LOOPBACK TRANSLATION',
    kind=Kind.CF_PATCH, category=Category.MIDI_USB, author='radiohagen',
    author_url='https://github.com/radiohagen/octatrack-modules',
    doc='Optional per-Part final-note translation, independently applied to INT/EXT/BOTH.',
    proof=Proof.PORT, proof_note='Emulator: note cleanup, native save/reload and panel pixels; hardware untested.',
    requires=('MIDI LOOPBACK','MIDI PART STATE','STORE'),
    linked=(Linked('loopbacktranslation',str(SOURCE/'translation.s'),cpu='54455',dram=True),
            Linked('loopbacktranslationfiles',str(SOURCE/'translation-files.s'),cpu='54455',dram=True),
            Linked('loopbacktranslationabi',str(SOURCE/'translation-abi.s'),dram=True)),
    gates=(Gate('tools/verify/verify_midi_loopback_translation.py',stage='image',venv=True),
           Gate('tools/verify/verify_midi_loopback_translation_store.py',stage='image',venv=True)),
)
