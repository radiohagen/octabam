"""PIO first-sector fix alone on the stock effects."""
from remix.schema import Proof, Remix
REMIX = Remix(
    name="pio-write-fix", family="mods", proof=Proof.CHECK,
    proof_note='',
    doc="The stock PIO first-sector fix, independently of STEM REC.",
    modules=("PIO WRITE FIX", "FILTER", "EQUALIZER", "DJ EQ", "PHASER",
             "FLANGER", "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR",
             "LO-FI", "DELAY", "PLATE REV", "SPRING REV", "DARK REV"),
    fallback="NONE",
)
