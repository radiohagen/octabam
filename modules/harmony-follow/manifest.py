"""Use one event dispatcher when Harmony and Follow share MIDI output."""
from pathlib import Path
from remix.registry import _load_one
from remix.schema import Category, Gate, Kind, Module, Override, Proof

HERE = Path(__file__).parent
FOLLOW = _load_one(HERE.parent / 'midi-follow/manifest.py')
HARMONY = _load_one(HERE.parent / 'midi-harmony/manifest.py')
EVENT_SITES = (0x4009c3d4, 0x4009c4d4, 0x4009fbb2, 0x4009fcfa)
SHARED = tuple(d for d in FOLLOW.detours if d.site in EVENT_SITES)
HARMONY_SITES = {d.site: d for d in HARMONY.detours}
assert len(SHARED) == len(EVENT_SITES)
for detour in SHARED:
    other = HARMONY_SITES[detour.site]
    assert (detour.expect, detour.kind, detour.pad_to) == (other.expect, other.kind, other.pad_to)

MODULE = Module(
    name='harmony-follow', key='HARMONY FOLLOW', kind=Kind.CF_PATCH,
    category=Category.PARTS, author='radiohagen',
    author_url='https://github.com/radiohagen/octatrack-modules', proof=Proof.CHECK,
    proof_note='',
    doc='Single transport and successful-note dispatcher for Harmony and Follow.',
    requires=('MIDI HARMONY', 'MIDI FOLLOW'),
    detours=SHARED,
    gates=(Gate('tools/verify/verify_harmony_follow_port.py', stage='image', venv=True),),
    overrides=tuple(Override(site, module) for site in EVENT_SITES
                    for module in ('MIDI HARMONY', 'MIDI FOLLOW')),
)
