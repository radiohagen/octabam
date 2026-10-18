"""cfmeter-post -- cfmeter with USB LAYOUT TRACKS POST in place of TRACKS MAIN CUE,
for that layout's ColdFire cost on a unit. cfmeter: octatrick without TUNER and the
USB input, plus CF METER and CF METER IDLE: the ColdFire's
spare time with SYNTH MACHINE voices running, read out over USB audio from
track 8.
DARK REV is off the chooser: its words hold the readout insert."""

from remix.schema import Proof, Remix

REMIX = Remix(
    name="cfmeter-post",
    family="probes", proof=Proof.PORT, proof_note="the readout chain under the port",
    doc="octatrick (less TUNER and the USB input) + CF METER on T8's FX2, with USB LAYOUT TRACKS POST in place of TRACKS MAIN CUE: the layout's ColdFire cost, over USB.",
    modules=("DIRECT JUMP", "SCALE QUANTIZER", "SYNTH MACHINE",
             "USB", "CF METER", "CF METER IDLE",
             "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER", "CHORUS",
             "SPATIALIZER", "COMB FILTER", "COMPRESSOR", "LO-FI", "DELAY",
             "PLATE REV", "SPRING REV"),
    fallback="NONE",
    settings={("octabam.usb", "LAYOUT"): "TRACKS POST",
              ("octabam.usb", "INPUTS"): "OFF"},
)
