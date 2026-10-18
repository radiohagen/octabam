from remix.schema import Proof, Remix

REMIX = Remix(
    name="rnd-name",
    family="test",
    proof=Proof.RENDER,
    proof_note="RND NAME smoke",
    doc="smoke: RND NAME alone",
    modules=("RND NAME",),
    fallback="NONE",
)
