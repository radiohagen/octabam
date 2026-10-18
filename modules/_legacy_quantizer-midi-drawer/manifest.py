"""Preserve native MIDI octave drawing beside SCALE QUANTIZER."""
from remix.schema import Category, Detour, Gate, Kind, Linked, Module, Proof

MODULE = Module(
    name='quantizer-midi-drawer', key='QUANTIZER MIDI DRAWER', kind=Kind.CF_PATCH,
    category=Category.FIXES, author='radiohagen',
    author_url='https://github.com/radiohagen/octatrack-modules',
    proof=Proof.CHECK, proof_note='',
    doc='Keep the native MIDI chromatic octave stack argument beside Scale Quantizer.',
    requires=('SCALE QUANTIZER',),
    linked=(Linked('qzmididrawer', 'modules/quantizer-midi-drawer/drawer.s', dram=True),),
    detours=(Detour(0x400449ae, bytes.fromhex('2039400beba2'),
                    'qzmididrawer', 'qz_midi_octave',
                    'MIDI branch bypasses the audio octave detour and pushes its native argument'),),
    gates=(Gate('tools/verify/verify_quantizer_midi_drawer.py', stage='image', venv=True),),
)
