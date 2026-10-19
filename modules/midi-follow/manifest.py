"""Per-MIDI-track root follower with native Part settings."""
from pathlib import Path
from remix.schema import Category, Claims, Detour, Gate, Kind, Linked, Module, Proof, Poke, SymbolRef

ROOT = Path(__file__).resolve().parent

def harmony_inc(modules, remix=None):
    return ('.set HAVE_HARMONY,1\n' if 'MIDI HARMONY' in modules else '') + ('.set HAVE_SCALES,1\n' if 'MIDI SCALES' in modules else '') + ('.set HAVE_LOOPBACK,1\n' if 'MIDI LOOPBACK' in modules else '')


MODULE = Module(
    name="midi-follow", key="MIDI FOLLOW", kind=Kind.CF_PATCH,
    category=Category.MIDI_USB, author='radiohagen', author_url="https://github.com/radiohagen/octatrack-modules",
    proof=Proof.PORT, proof_note='',
    doc="RFOL follows source notes; press D for FIXED/GRAV/SOURCE register, OCT/OFFS and TRIG/LIVE updates.",
    requires=('MIDI PART STATE',),
    conflicts=(("EUCLID", "shared transport start/resume detours need a composition bridge"),),
    linked=(Linked("bassfollow", str(ROOT / "midi_follow.s"), dram=True, include=harmony_inc),
            Linked("followresponse", str(ROOT / "response.s"), dram=True, include=harmony_inc),
            Linked("followevents", str(ROOT / "events.s"), dram=True, include=harmony_inc),
            Linked("followregister", str(ROOT / "register.s"), dram=True),
            Linked("followgravity", str(ROOT / "gravity.s"), dram=True),
            Linked("followgravityaccess", str(ROOT / "gravity-access.s"), dram=True),
            Linked("followsettings", str(ROOT / "settings.s"), dram=True),
            Linked("followpage", str(ROOT / "page.s"), dram=True)),
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
        Poke(0x400d4086, bytes.fromhex('00000001'), bytes.fromhex('00000050'), 'Follow fixed octave / biased source offset packed range'),
        Poke(0x400d408e, bytes.fromhex('00000001'), bytes.fromhex('00000030'), 'Follow home octave / register mode packed range'),
        Poke(0x400d4035, b'\x00', b'\x23', 'Follow FIXED octave 3, SOURCE offset zero'),
        Poke(0x400d4037, b'\x00', b'\x03', 'Follow GRAV home octave 3, mode FIXED'),
    ),
    claims=Claims(part_window=tuple((0x4e2+36*t+f, 1, 'Follow Part setting') for t in range(8) for f in (3,13,15))),
    detours=(Detour(0x4009c3d4, bytes.fromhex('23c0800065b8'),
                    'followevents', 'bf_start_a', 'reset Follow register on transport start'),
             Detour(0x4009c4d4, bytes.fromhex('23c0800065b8'),
                    'followevents', 'bf_start_b', 'reset Follow register on transport resume'),
             Detour(0x4009fbb2, bytes.fromhex('7339400d807c'),
                    'followevents', 'bf_sent_a', 'commit Follow register after successful note-on'),
             Detour(0x4009fcfa, bytes.fromhex('7139400d807c'),
                    'followevents', 'bf_sent_b', 'commit Follow register after ownership replacement'),
             Detour(0x4009F986, bytes.fromhex("41f980006676"),
                    "bassfollow", "bf_pre_capture", "capture all ordinary source triggers before any track emits"),
             Detour(0x40036674, bytes.fromhex("261524047003"),
                    "bassfollow", "bf_draw_value", "draw RFOL from per-track module RAM"),
             Detour(0x4009FB00, bytes.fromhex("2807e58c1d44ffd5"),
                   "bassfollow", "bf_capture",
                   "latch the original chord root independently of arp output", pad_to=8),
             Detour(0x4009FB80, bytes.fromhex("12126d0001a6"),
                   "bassfollow", "bf_note",
                   "resolve root before the sequencer records the emitted note"),),
    gates=(Gate('tools/verify/verify_midi_follow_notes.py', stage='image', venv=True),
           Gate('tools/verify/verify_midi_follow_gravity.py', stage='image', venv=True),
           Gate('tools/verify/verify_midi_follow_stress.py', stage='image', venv=True),
           Gate("tools/verify/verify_midi_follow_response.py", stage="image", venv=True),
           Gate("tools/verify/verify_midi_follow.py", stage="image", venv=True),
           Gate("tools/verify/verify_midi_follow_register.py", stage="image", venv=True)),
)
