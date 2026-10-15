"""Per-track internal MIDI routing with a native CHAN-press window."""
from remix.schema import Category, Detour, Gate, Kind, Linked, Module, Proof, SymbolRef

MODULE = Module(
    name="midi-loopback", key="MIDI LOOPBACK", kind=Kind.CF_PATCH,
    category=Category.MIDI_USB, author="mattiaswolff",
    author_url="https://github.com/mattiaswolff",
    doc="Press CHAN for per-Part EXT/INT/BOTH routing of MIDI-track notes and controls.",
    proof=Proof.PORT, proof_note="Panel, native Part persistence and routing under emulator; no hardware",
    requires=("MIDI PART STATE",),
    linked=(Linked("loopback", "modules/midi-loopback/loopback.s", cpu="54455", dram=True),
            Linked("loopbackproducers", "modules/midi-loopback/producers.s", dram=True,
                   include=lambda modules: '.set HAVE_SCENES_BRIDGE,1\n' if 'MIDI LOOPBACK SCENES' in modules else ''),
            Linked("loopbacksettings", "modules/midi-loopback/settings.s", dram=True),
            Linked("loopbackpage", "modules/midi-loopback/page.s", dram=True)),
    detours=(
        *(Detour(site, bytes.fromhex("41f946c7febe"), "loopbackproducers", "lb_rx_map",
                 "internal receive map excludes MIDI-track forwarding", kind="jsr")
          for site in (0x4000a3fe,0x4000a53a,0x4000a654,0x4000da58,0x4000e058,0x4000e7bc)),
        Detour(0x4009f288, bytes.fromhex("4fefffec48d70c1c"),
               "loopbackproducers", "lb_panic", "panic follows assigned track destinations", pad_to=8),
        Detour(0x4009f794, bytes.fromhex("4e56ff9848d73cfc"),
               "loopback", "lb_tick", "release held destinations after route/channel changes", pad_to=8),
        Detour(0x40005558, bytes.fromhex("487946c7e9744e93"),
               "loopback", "lb_receive", "MIDI task receives complete internal messages", pad_to=8),
        Detour(0x4009f26e, bytes.fromhex("4cd77cfc4fef003c"),
               "loopbackproducers", "lb_control_tail", "route live CC/bend/pressure before restoring source track", pad_to=8),
    ),
    symbol_refs=tuple(SymbolRef(site, 0x40010bc8, "loopback", "lb_send",
                                "route a proven MIDI-track producer before DIN/USB")
                      for site in (0x4009fbae, 0x4009fcf6, 0x4009feee, 0x4009ffba,
                                   0x4009f8be, 0x4009fc50, 0x4009fcd4,
                                   0x4009f328, 0x400a0020)) + tuple(
        SymbolRef(site, 0x40010bc8, "loopbackproducers", symbol, "route track-owned channel output")
        for symbol, sites in (
            ("lb_track_send", (0x4009fdc0, 0x4009fe2e)),
            ("lb_key_send", (0x4009ea68, 0x4009ea96, 0x4009eb50)),
            ("lb_setup_send", (0x4009ecb4,)),
            ("lb_control_send", (0x4009efe4, 0x4009f096, 0x4009f236)),
        ) for site in sites) + (
        SymbolRef(0x400bc556, 0x4004ae08, "loopbackpage", "lb_channel_press", "confirm CHAN then open MIDI ROUTING"),
        SymbolRef(0x400d3f20, 0x4003c770, "loopbackpage", "lb_channel_format", "CHAN internal/both marker"),),
    gates=(Gate("tools/verify/verify_midi_loopback_producers.py", venv=True, stage="image"),
           Gate('tools/verify/verify_midi_loopback_settings.py', venv=True, stage='image'),
           Gate('tools/verify/verify_midi_loopback_stress.py', venv=True, stage='image'),
           Gate("tools/verify/verify_midi_loopback.py", venv=True, stage="image"),),
)
