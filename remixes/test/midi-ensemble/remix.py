"""All MIDI modules with KITS/Scenes/P2 on stock audio effects."""
from remix.schema import Pin, Proof, Remix
REMIX = Remix(
    name='midi-ensemble', family='mods', proof=Proof.CHECK,
    proof_note='verify_integrated_retention_port and verify_midi_concert_port: emulator evidence; hardware pending',
    doc='Scales, Follow and Harmony with KITS, MIDI SCENES and upstream P2 retention and track-local Harmony.',
    modules=('STORE', 'KITS', 'MIDI SCENES', 'MIDI SRAM', 'MIDI PART STATE',
             'MIDI FOLLOW', 'MIDI SCALES', 'MIDI HARMONY', 'HARMONY PLOCKS',
             'SCENES P2', 'PLOCKS P2',
             'FILTER', 'EQUALIZER', 'DJ EQ', 'PHASER', 'FLANGER', 'CHORUS',
             'SPATIALIZER', 'COMB FILTER', 'COMPRESSOR', 'LO-FI', 'DELAY',
             'PLATE REV', 'SPRING REV', 'DARK REV'),
    settings={('mattias.midi-harmony','RETENTION'):Pin('MIDI TRACK')},
    fallback='NONE',
)
