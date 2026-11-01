"""LEVEL/mute/solo/scene-XLV sends with participation independent of volume.

The ColdFire scales transient DEL/REV records and tags their original send
participation in bit 15. The matching, module-selected DSP path removes that
tag before arithmetic and uses it for client counts. Muting a source reduces
its excitation without raising the remaining sources' normalization gain.
Scene XLV scales only new excitation; the engines keep their existing tails.
AMP VOL, XVOL and envelopes already affect the source audio entering SEND.
The Part, panel, MIDI feedback and project formats are unchanged.
"""

import pathlib
import runpy

from remix import schema
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
    # Reuse TRACKS POST's validated extraction from the user's stock image.
    # Q15 is relative to unlocked XLV (127 << 8, table index 254), so adding
    # scene following leaves all previous no-scene send coefficients exact.
    # Entry 255 is above the published 0..0x7f00 range; cap it at that unity.
    root = pathlib.Path(schema.__file__).resolve().parents[2]
    words = runpy.run_path(str(root / "modules/usb/manifest.py"))["xlv_table"]()
    full = words[254]
    gains = [min(0x8000, ((w << 15) + full // 2) // full) for w in words]
    lines.append("        .macro PF_XLV_TABLE\n")
    for i in range(0, len(gains), 8):
        lines.append("        .word " + ", ".join(f"0x{g:04x}" for g in gains[i:i + 8]) + "\n")
    lines.append("        .endm\n")
    return "".join(lines)


MODULE = Module(
    name="post-fader",
    key="POST FADER",
    kind=Kind.CF_PATCH,
    category=Category.BUS, author="sanderlegit", author_url="https://github.com/sanderlegit",
    proof=Proof.PORT, proof_note="13008 hook cases, 8 scene/AMP volume fixtures, 10 mute/fader fixtures, 4 sounding-host fixtures and 212 returns cases pass; DSP uploads unchanged; hardware acceptance pending",
    doc="The bus sends follow LEVEL, mute, solo and scene XLEV while keeping each original "
        "send's normalization share; source fades preserve engine state and other sources' gain.",
    linked=(Linked("postfader", "modules/post-fader/postfader.s", dram=True, include=ids_inc),),
    detours=(
        Detour(0x4000d0e4, H("4eb940004bd4"), "postfader", "pf_frame",
               "frame routine: the record builder, then the sends x the tracks' mix gains",
               kind="jsr"),
    ),
    requires=("SEND",),
    gates=(Gate("tools/verify/verify_postfader_hook.py", venv=True, stage="image"),
           Gate("tools/verify/verify_postfader_dsp.py", stage="image"),
           Gate("tools/verify/verify_postfader.py", venv=True),
           Gate("tools/verify/verify_postfader_hosts.py", venv=True, stage="image"),
           Gate("tools/verify/verify_postfader_volume.py", venv=True, stage="image"),),
)
