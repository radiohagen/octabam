"""waveload-port -- waveload without CF METER IDLE, for the port gate: the
port advances its clock only at main's stock `bras .`."""

from remix.schema import Proof, Remix

REMIX = Remix(
    name="waveload-port",
    family="probes", proof=Proof.PORT, proof_note="the load path under the port",
    doc="waveload without the idle loop: the port gate for the wave engines in the frame interrupt.",
    modules=("USB", "CF METER", "WAVE LOAD",
             "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER", "CHORUS",
             "SPATIALIZER", "COMB FILTER", "COMPRESSOR", "LO-FI", "DELAY",
             "PLATE REV", "SPRING REV"),
    fallback="NONE",
    settings={("octabam.usb", "LAYOUT"): "TRACKS MAIN CUE",
              ("octabam.usb", "INPUTS"): "OFF"},
)
