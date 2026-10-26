"""LEVEL/mute/solo-aware sends with participation independent of the fader.

The ColdFire scales transient DEL/REV records and tags their original send
participation in bit 15. The matching, module-selected DSP path removes that
tag before arithmetic and uses it for client counts. Muting a source reduces
its excitation without raising the remaining sources' normalization gain.
The Part, panel, MIDI feedback and project formats are unchanged.
"""

from remix.schema import Category, Detour, Gate, Kind, Linked, Module, Proof

H = bytes.fromhex


def ids_inc(modules, remix):
    """Only selected bus consumers, with this remix's already-bound IDs.

    Absent engines must not match stock SPRING/DARK at their preferred IDs.
    Id zero participates only when the selected fallback is SEND.
    """
    lines = [f"        .set    PF_FALLBACK_SEND, {int(remix.fallback == 'SEND')}\n"]
    for name, key in (("ID_SEND", "SEND"), ("ID_DELAY", "DELAY SERVER"),
                      ("ID_VERB", "REVERB SERVER")):
        if key in modules:
            lines.append(f"        .set    {name}, {modules[key].menu.fx2_id}\n")
    return "".join(lines)


MODULE = Module(
    name="post-fader",
    key="POST FADER",
    kind=Kind.CF_PATCH,
    category=Category.BUS, author="sanderlegit", author_url="https://github.com/sanderlegit",
    proof=Proof.PORT, proof_note="6144 hook cases, held-note DSP comparisons and 10 firmware audio cases passed; hardware acceptance pending",
    doc="The bus sends follow LEVEL, mute and solo while keeping each original send's "
        "normalization share; muting a source leaves other sources' gain unchanged.",
    linked=(Linked("postfader", "modules/post-fader/postfader.s", dram=True, include=ids_inc),),
    detours=(
        Detour(0x4000d0e4, H("4eb940004bd4"), "postfader", "pf_frame",
               "frame routine: the record builder, then the sends x the tracks' mix gains",
               kind="jsr"),
    ),
    requires=("SEND",),
    gates=(Gate("tools/verify/verify_postfader_hook.py", venv=True, stage="image"),
           Gate("tools/verify/verify_postfader_dsp.py", stage="image"),
           Gate("tools/verify/verify_postfader.py", venv=True),),
)
