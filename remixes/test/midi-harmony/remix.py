"""Per-track HARM on MIDI NOTE SETUP; scale notes and chords before the stock arp."""
from remix.schema import Proof, Remix

REMIX = Remix(
    name="midi-harmony", family="mods", proof=Proof.PORT,
    proof_note="verify_midi_harmony: emulator verification; not flashed",
    doc="Per-track HARM on MIDI NOTE SETUP; scale notes and chords before the stock arp.",
    modules=("STORE", "MIDI PART STATE", "MIDI HARMONY", "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER",
             "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR", "LO-FI",
             "DELAY", "PLATE REV", "SPRING REV", "DARK REV"),
    fallback="NONE",
)
