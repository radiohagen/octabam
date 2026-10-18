"""EUCLID FILL -- TRACK + PAGE opens a standalone Euclidean trig-fill page.

Hold any track key and press PAGE: a window with STEPS / PULSE / ROT.
STEPS is the pattern (or PER-TRACK) length — not editable. Encoder A =
PULSE, B = ROT. YES writes sample trigs on the held tracks (or the current
track if none were held when the window opened). NO or TRACK+PAGE again
closes.

Independent of PROJECT > SEQUENCER (SCALE QUANTIZER) and of the EUCLID
DSP effect. FUNC + PAGE (SCALE SETUP) stays stock.
"""

from remix.schema import Category, Detour, Gate, Kind, Linked, Module, Proof

H = bytes.fromhex

# PAGE opener prologue: lea -16(sp),sp ; movem.l d2-d4/a2,(sp)  (8 B)
PAGE = 0x4004ffc4
PAGE_STOCK = H("4feffff048d7041c")

MODULE = Module(
    name="euclid-fill",
    key="EUCLID FILL",
    kind=Kind.CF_PATCH,
    category=Category.MACHINES,
    author="octabam",
    author_url="https://github.com/sambanks/octabam",
    proof=Proof.HARDWARE,
    proof_note="cursory testing on Sam's MKII (owner report, 16 Oct 2026); " "builds and boots under the port; fill math gated in verify_euclid_fill",
    doc="TRACK + PAGE: Euclidean sample-trig fill (STEPS=pattern len / PULSE / ROT; A/B knobs).",
    linked=(Linked("ef", "modules/euclid-fill/euclid_fill.s", dram=True),),
    detours=(
        Detour(PAGE, PAGE_STOCK, "ef", "ef_page",
               "PAGE: with a track held, toggle the Euclid fill window",
               pad_to=8),
    ),
    gates=(Gate("tools/verify/verify_euclid_fill.py", venv=True, stage="image"),),
)
