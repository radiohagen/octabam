"""Loopback prototype on stock effects, isolated from personal remixes."""
from remix.schema import Proof, Remix

REMIX = Remix(
    name="midi-loopback-follow", family="mods", proof=Proof.PORT,
    proof_note='',
    doc="MIDI Loopback routing with Follow, Harmony and Scales; native Part settings.",
    modules=("MIDI PART STATE", "MIDI LOOPBACK", "MIDI FOLLOW", "MIDI SCALES", "MIDI SRAM", "MIDI HARMONY", "STORE", "FILTER", "EQUALIZER", "DJ EQ", "PHASER",
             "FLANGER", "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR",
             "LO-FI", "DELAY", "PLATE REV", "SPRING REV", "DARK REV"),
    fallback="NONE",
)
