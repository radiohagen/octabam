"""Stock effects and per-track MIDI root following."""
from remix.schema import Proof, Remix

REMIX = Remix(
    name="midi-follow", family="mods", proof=Proof.PORT,
    proof_note='',
    doc="Per-track RFOL source selection on MIDI NOTE SETUP; Part-owned root following.",
    modules=("MIDI PART STATE", "MIDI FOLLOW", "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER",
             "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR", "LO-FI",
             "DELAY", "PLATE REV", "SPRING REV", "DARK REV"),
    fallback="NONE",
)
