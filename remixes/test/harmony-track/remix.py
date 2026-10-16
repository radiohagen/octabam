"""Per-track HARM on MIDI NOTE SETUP; scale notes and chords before the stock arp."""
from remix.schema import Pin, Proof, Remix

REMIX = Remix(
    name="harmony-track", family="mods", proof=Proof.PORT,
    proof_note='',
    doc="Per-track HARM on MIDI NOTE SETUP; scale notes and chords before the stock arp.",
    modules=("STORE", "MIDI PART STATE", "MIDI SRAM", "MIDI HARMONY", "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER",
             "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR", "LO-FI",
             "DELAY", "PLATE REV", "SPRING REV", "DARK REV"),
    fallback="NONE",
    settings={("mattias.midi-harmony", "RETENTION"): Pin("MIDI TRACK")},
)
