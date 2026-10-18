"""stock effects with EUCLID FILL: TRACK+PAGE Euclidean trig-fill page."""

from remix.schema import Proof, Remix

REMIX = Remix(
    name="euclid-fill",
    family="mods", proof=Proof.CHECK, proof_note="",
    doc="stock effects with EUCLID FILL: TRACK+PAGE Euclidean trig-fill page.",
    modules=("EUCLID FILL",
             "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER",
             "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR", "LO-FI",
             "DELAY", "PLATE REV", "SPRING REV", "DARK REV"),
    fallback="NONE",
)
