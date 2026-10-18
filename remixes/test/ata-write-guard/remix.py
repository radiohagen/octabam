"""The first-sector PIO write guard on the stock effects."""
from remix.schema import Proof, Remix

REMIX = Remix(
    name="ata-write-guard", family="mods", proof=Proof.PORT,
    proof_note="forced completion-interrupt gate under the port; not on hardware",
    doc="Stock effects with the first PIO card write guarded through bookkeeping.",
    modules=("ATA WRITE GUARD", "FILTER", "EQUALIZER", "DJ EQ", "PHASER",
             "FLANGER", "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR",
             "LO-FI", "DELAY", "PLATE REV", "SPRING REV", "DARK REV"),
    fallback="NONE",
)
