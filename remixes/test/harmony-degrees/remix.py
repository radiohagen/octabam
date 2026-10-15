"""MIDI Harmony with all seven scale modes."""
from remix.schema import Proof, Remix

REMIX = Remix(
    name='harmony-degrees', family='mods', proof=Proof.CHECK,
    proof_note='verify_harmony_degree_integration: linked degree component checks; hardware untested',
    doc='MIDI Harmony degree/register roots with all seven scale modes.',
    modules=('STORE', 'MIDI PART STATE', 'MIDI HARMONY', 'MIDI SCALES',
             'FILTER', 'EQUALIZER', 'DJ EQ', 'PHASER', 'FLANGER', 'CHORUS',
             'SPATIALIZER', 'COMB FILTER', 'COMPRESSOR', 'LO-FI', 'DELAY',
             'PLATE REV', 'SPRING REV', 'DARK REV'),
    fallback='NONE',
)
