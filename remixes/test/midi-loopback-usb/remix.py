"""Loopback and USB-MIDI hook compatibility on stock effects."""
from remix.schema import Proof, Remix

REMIX = Remix(
    name="midi-loopback-usb", family="mods", proof=Proof.PORT,
    proof_note='',
    doc="Stock effects with the loopback prototype and USB-MIDI for compatibility gates.",
    modules=("MIDI PART STATE", "MIDI LOOPBACK", "USB MIDI", "FILTER", "EQUALIZER", "DJ EQ", "PHASER",
             "FLANGER", "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR",
             "LO-FI", "DELAY", "PLATE REV", "SPRING REV", "DARK REV"),
    fallback="NONE",
)
