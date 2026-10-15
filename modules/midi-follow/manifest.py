"""Per-MIDI-track root follower with native Part settings."""
from remix.schema import Category, Claims, Detour, Gate, Kind, Linked, Module, Proof, Poke, SymbolRef

def harmony_inc(modules):
    return ('.set HAVE_HARMONY,1\n' if 'MIDI HARMONY' in modules else '') + ('.set HAVE_SCALES,1\n' if 'MIDI SCALES' in modules else '') + ('.set HAVE_LOOPBACK,1\n' if 'MIDI LOOPBACK' in modules else '')


MODULE = Module(
    name="midi-follow", key="MIDI FOLLOW", kind=Kind.CF_PATCH,
    category=Category.MIDI_USB, author="Mattias Wolff", author_url="https://github.com/mattiaswolff/octabam",
    proof=Proof.PORT, proof_note="verify_midi_follow: stock/patched MIDI capture; not flashed",
    doc="RFOL selects a source; press D for fixed or source-relative octave, then follower TRAN/P-locks.",
    requires=('MIDI PART STATE',),
    linked=(Linked("bassfollow", "modules/midi-follow/midi_follow.s", dram=True, include=harmony_inc),
            Linked("followresponse", "modules/midi-follow/response.s", dram=True, include=harmony_inc),
            Linked("followregister", "modules/midi-follow/register.s", dram=True),
            Linked("followsettings", "modules/midi-follow/settings.s", dram=True),
            Linked("followpage", "modules/midi-follow/page.s", dram=True)),
    symbol_refs=(
        SymbolRef(0x400bc5a4, 0x4004ae08, "followpage", "bf_page_open", "RFOL D press opens register settings"),
        SymbolRef(0x400bc5a8, 0x4004ae08, "followpage", "bf_page_noop", "RFOL D release leaves settings open"),
        SymbolRef(0x400BC64E, 0x4003A8E8, "bassfollow", "bf_encoder", "NOTE SETUP D encoder"),
        SymbolRef(0x400D3F2C, 0, "bassfollow", "bf_format", "RFOL OFF/T1-T8 formatter"),
    ),
    pokes=(
        Poke(0x400D3F5C, bytes(4), bytes.fromhex("400467a4"), "RFOL text widget, like CHAN"),
        Poke(0x400D3E8A, b"----\0\0", b"RFOL\0\0", "NOTE SETUP D label"),
        Poke(0x400D3EFC, bytes.fromhex("00000080"), bytes.fromhex("00000009"), "RFOL nine values"),
        Poke(0x400D3FCB, b"\x01", b"\x11", "enable NOTE SETUP D only"),
        Poke(0x400d4086, bytes.fromhex('00000001'), bytes.fromhex('0000000b'), 'Follow fixed octave Part range'),
        Poke(0x400d408e, bytes.fromhex('00000001'), bytes.fromhex('00000005'), 'Follow relative octave Part range'),
        Poke(0x400d4035, b'\x00', b'\x03', 'Follow fixed octave default 3'),
        Poke(0x400d4037, b'\x00', b'\x02', 'Follow relative octave default zero biased by two'),
    ),
    claims=Claims(part_window=tuple((0x4e2+36*t+f, 1, 'Follow Part setting') for t in range(8) for f in (3,13,15))),
    detours=(Detour(0x4009F986, bytes.fromhex("41f980006676"),
                    "bassfollow", "bf_pre_capture", "capture all ordinary source triggers before any track emits"),
             Detour(0x40036674, bytes.fromhex("261524047003"),
                    "bassfollow", "bf_draw_value", "draw RFOL from per-track module RAM"),
             Detour(0x4009FB00, bytes.fromhex("2807e58c1d44ffd5"),
                   "bassfollow", "bf_capture",
                   "latch the original chord root independently of arp output", pad_to=8),
             Detour(0x4009FB80, bytes.fromhex("12126d0001a6"),
                   "bassfollow", "bf_note",
                   "resolve root before the sequencer records the emitted note"),),
    gates=(Gate('tools/verify/verify_midi_follow_stress.py', stage='image', venv=True),
           Gate("tools/verify/verify_midi_follow_response.py", stage="image", venv=True),
           Gate("tools/verify/verify_midi_follow.py", stage="image", venv=True),
           Gate("tools/verify/verify_midi_follow_register.py", stage="image", venv=True)),
)
