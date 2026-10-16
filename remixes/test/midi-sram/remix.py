"""Stock effects and the shared native MIDI Part boundary."""
from remix.schema import Proof, Remix

REMIX = Remix(
    name='midi-sram', family='mods', proof=Proof.PORT,
    proof_note='',
    doc='Shared native MIDI Part access and copy/clear boundary, without consumer modules.',
    modules=('MIDI SRAM', 'MIDI PART STATE', 'FILTER', 'EQUALIZER', 'DJ EQ', 'PHASER', 'FLANGER',
             'CHORUS', 'SPATIALIZER', 'COMB FILTER', 'COMPRESSOR', 'LO-FI',
             'DELAY', 'PLATE REV', 'SPRING REV', 'DARK REV'),
    fallback='NONE',
)
