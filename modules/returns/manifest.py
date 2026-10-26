"""T8 controls for independent delay and reverb returns.

The servers keep their tails running independently of T1/T5's track mix gains.
Payload A publishes the return levels and mixes the wet buffers. Payload B's
init/proc immediately return; declaring it lets this one module own the shared
producer/consumer allocation on both cores without overlapping ledger claims.
BusVerb owns the private Y return buffer/state used by both routed and fallback
prints when RETURNS is selected; unselected engine sources stay unchanged.
"""

from remix.schema import (Category, Claims, DspHook, DspRange, DspSection,
                          Gate, Harness, Kind, MenuEntry, Module, Param, Proof, YBase)

_BLANK = Param(b"", None, active=False)

MODULE = Module(
    name="returns", key="RETURNS", kind=Kind.DSP_CLIENT,
    category=Category.BUS, author="sambanks", author_url="https://github.com/sambanks",
    proof=Proof.CHECK, proof_note="212 exact DSP cases verify installed bytes, gain/mix, freshness and track/core guards; hardware acceptance pending",
    doc="Independent DLY/VRB return levels on T8; into the master input or MAIN.",
    menu=MenuEntry(fx2_id=0x1b, donor_desc=0x400d4772,
                   abbr=b"RETN", fullname=b"Returns", build_tag=False),
    params=(
        Param(b"DLY", 108, active=True,
              doc="delay return level, using the track LEVEL gain law"),
        Param(b"VRB", 108, active=True,
              doc="reverb return level, using the track LEVEL gain law"),
        _BLANK, _BLANK, _BLANK, _BLANK,
        _BLANK, _BLANK, _BLANK, _BLANK, _BLANK, _BLANK,
    ),
    dsp=DspSection(
        asm="modules/returns/returns.asm", priority=25,
        payloads=frozenset({"A", "B"}), ybase=YBase.NEVER,
        hooks=(DspHook({"A": 0x2d5}, (0x60f000, 0x000206), "mixhook",
                       "mixdown: independent returns into T8's input or MAIN"),),
        subst={"A": {"@RETURNS_CORE_GUARD@": "; core 0 owns the returns"},
               "B": {"@RETURNS_CORE_GUARD@": "rts"}},
        max_per_core=1,
    ),
    claims=Claims(dsp_ranges=(
        DspRange("y", 0x30100, 0x109, "delay return ring, stamps and liveness"),
    )),
    harness=Harness(layout_char=None, is_server=False),
    requires=("REVERB SERVER", "DELAY SERVER"),
    gates=(Gate("tools/verify/verify_returns.py", stage="image"),),
)
