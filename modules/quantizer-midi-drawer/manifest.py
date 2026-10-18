"""Compatibility selection name; upstream #741 supplies the MIDI drawer fix."""
from remix.schema import Category, Gate, Kind, Module, Proof

MODULE = Module(
    name='quantizer-midi-drawer', key='QUANTIZER MIDI DRAWER', kind=Kind.CF_PATCH,
    category=Category.FIXES, author='radiohagen',
    author_url='https://github.com/radiohagen/octatrack-modules',
    proof=Proof.CHECK, proof_note='',
    doc='Compatibility name for upstream native MIDI octave drawing; no additional hooks.',
    requires=('SCALE QUANTIZER',),
    gates=(Gate('tools/verify/verify_quantizer_ui.py', once=True, venv=True),),
)
