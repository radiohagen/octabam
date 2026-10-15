"""Harmony and compressed PLOCKS P2 integration on stock effects."""
from remix.schema import Pin, Proof, Remix

REMIX = Remix(
    name='harmony-plocks', family='mods', proof=Proof.CHECK,
    proof_note='verify_harmony_plocks: linked bridge and persistence checks; not flashed',
    doc='Harmony and PLOCKS P2 shared-hook integration with SCENES P2.',
    modules=('MIDI PART STATE', 'MIDI HARMONY', 'MIDI SCALES',
             'STORE', 'SCENES P2', 'PLOCKS P2', 'HARMONY PLOCKS',
             'FILTER', 'EQUALIZER', 'DJ EQ', 'PHASER', 'FLANGER', 'CHORUS',
             'SPATIALIZER', 'COMB FILTER', 'COMPRESSOR', 'LO-FI', 'DELAY',
             'PLATE REV', 'SPRING REV', 'DARK REV'),
    fallback='NONE',
)
