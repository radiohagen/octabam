"""Stock effects and the shared native MIDI Part boundary."""
from remix.schema import Proof, Remix

REMIX = Remix(
    name='midi-part-state', family='mods', proof=Proof.PORT,
    proof_note='verify_midi_part_copy: linked native publication and copy checks; not flashed',
    doc='Shared native MIDI Part access and copy/clear boundary, without consumer modules.',
    modules=('MIDI PART STATE', 'FILTER', 'EQUALIZER', 'DJ EQ', 'PHASER', 'FLANGER',
             'CHORUS', 'SPATIALIZER', 'COMB FILTER', 'COMPRESSOR', 'LO-FI',
             'DELAY', 'PLATE REV', 'SPRING REV', 'DARK REV'),
    fallback='NONE',
)
