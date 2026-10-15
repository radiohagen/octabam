"""Experimental protected retained pool; see README before composing."""
from remix.schema import Category, Claims, Gate, Kind, Linked, Module, Poke, Proof
H = bytes.fromhex
# Only MIDI loops. Audio field 31 is a sample lock and must stay native.
LOOPS = (
    (0x4002adc8, '7020', '701e', 'MIDI page paste'),
    (0x4002c766, '7020', '701e', 'MIDI trig paste'),
    (0x400387e6, '7020', '701e', 'MIDI masked clear'),
    (0x400397d0, '7020', '701e', 'MIDI page clear'),
    (0x40039b9e, '7020', '701e', 'MIDI track clear'),
    (0x40040dd4, '7020', '701e', 'MIDI held-lock clear'),
    (0x4005fe08, '3c3c0020', '3c3c001e', 'MIDI trig toggle'),
    (0x4009ceaa, '7220', '721e', 'MIDI step duplication'),
)
MODULE = Module(
    name='midi-sram', key='MIDI SRAM', kind=Kind.CF_PATCH,
    category=Category.PARTS, author='Mattias Wolff',
    author_url='https://github.com/radiohagen/octatrack-modules', proof=Proof.CHECK,
    proof_note='verify_midi_sram: bounded retained I/O and native copy protection; hardware untested',
    doc='Protected retained byte pool in native MIDI step padding.',
    requires=('MIDI PART STATE',),
    linked=(Linked('midisram', 'modules/midi-sram/pool.s', dram=True),),
    gates=(Gate('tools/verify/verify_midi_sram.py',stage='image',venv=True),),
    pokes=tuple(Poke(at,H(old),H(new),label+': keep CS1 padding') for at,old,new,label in LOOPS),
    claims=Claims(sram=tuple((0x1001614e+p*0x8ed8+0x4900+t*0x8b0+s*32+30, 2,
                             'MIDI step padding retained pool')
        for p in range(16) for t in range(8) for s in range(64))),
)
