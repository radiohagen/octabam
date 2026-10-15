"""Compose Harmony and PLOCKS P2 at their shared stock call sites."""
from dataclasses import replace
from pathlib import Path
from remix.registry import _load_one
from remix.schema import Category, Gate, Kind, Linked, Module, Override, Proof

HERE = Path(__file__).parent
HARMONY = _load_one(HERE.parent / 'midi-harmony/manifest.py')
PLOCKS = _load_one(HERE.parent / 'plocks-p2/manifest.py')
P2_SITES = {d.site: d for d in PLOCKS.detours}
SHARED = tuple(d for d in HARMONY.detours if d.site in P2_SITES)
for d in SHARED:
    other = P2_SITES[d.site]
    assert (d.expect, d.kind, d.pad_to) == (other.expect, other.kind, other.pad_to), hex(d.site)

MODULE = Module(
    name='harmony-plocks', key='HARMONY PLOCKS', kind=Kind.CF_PATCH,
    category=Category.PARTS, author='Mattias Wolff',
    author_url='https://github.com/mattiaswolff/octabam', proof=Proof.CHECK,
    proof_note='verify_harmony_plocks: combined copy, editing and STORE checks; hardware untested',
    doc='Shared editing and pattern/track copy hooks for Harmony and PLOCKS P2.',
    requires=('MIDI HARMONY', 'PLOCKS P2'),
    linked=(Linked('harmonyp2', 'modules/harmony-plocks/bridge.s', dram=True),),
    detours=tuple(replace(d, unit='harmonyp2', symbol='hpl_'+d.symbol,
                          note='Harmony and P2: '+d.note) for d in SHARED),
    overrides=tuple(Override(d.site, module) for d in SHARED
                    for module in ('MIDI HARMONY', 'PLOCKS P2')),
    gates=(Gate('tools/verify/verify_harmony_plocks.py', stage='image', venv=True),),
)
