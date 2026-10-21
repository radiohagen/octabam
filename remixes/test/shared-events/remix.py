"""All current shared-event clients, without combination-specific bridges."""
from remix.schema import Proof, Remix
REMIX = Remix(name='shared-events', family='mods', proof=Proof.CHECK, proof_note='',
    doc='Shared event platform with HARM, Follow, EUCLID and page-two locks.',
    modules=('SEQUENCER EVENTS','EDIT EVENTS','STORE','MIDI PART STATE','MIDI SRAM',
             'MIDI HARMONY','MIDI FOLLOW','MIDI SCALES','SCENES P2','PLOCKS P2',
             'EUCLID','FILTER','EQUALIZER','DJ EQ','PHASER','COMPRESSOR','LO-FI','DELAY','PLATE REV',
             'SPRING REV','DARK REV'),
    fx1=('EUCLID','FILTER','EQUALIZER','DJ EQ','PHASER','COMPRESSOR','LO-FI'),
    fallback='NONE')
