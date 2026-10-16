"""MIDI Follow with internal/external Loopback routing."""
from remix.schema import Proof, Remix

REMIX = Remix(
    name="midi-loopback-follow", family="mods", proof=Proof.PORT,
    proof_note='',
    doc="MIDI Loopback routing with Follow and shared native Part settings.",
    modules=("MIDI PART STATE", "MIDI LOOPBACK", "MIDI FOLLOW", "FILTER", "EQUALIZER", "DJ EQ", "PHASER",
             "FLANGER", "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR",
             "LO-FI", "DELAY", "PLATE REV", "SPRING REV", "DARK REV"),
    fallback="NONE",
)
