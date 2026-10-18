"""USB -- the composite USB device: MIDI in/out on EP2, the host as audio
out (EP3 IN) and in (EP3 OUT), one module where four stood until 14 Oct 2026
(USB MIDI, USB AUDIO OUT, USB AUDIO IN, USB CROSSBAR).

The LAYOUT and INPUTS settings choose the code (Apply.BUILD in this form;
run time is docs/proposals/USB.md phase 2):

  LAYOUT            which channels go to the host: the six layouts of the
                    old USB AUDIO OUT module (TRACKS MAIN CUE, TRACKS,
                    MASTER, MAIN CUE, MAIN, TRACKS POST), or OFF for USB
                    MIDI alone
  INPUTS            which inputs the host's channels stand in for (AB, CD,
                    ABCD, the old USB AUDIO IN values), or OFF for no
                    host -> device stream

INPUTS without a LAYOUT is refused: EP3 IN is the implicit-feedback source
for EP3 OUT. Every combination carries USB MIDI's units; the memory claims
are the ABCD maxima in every combination with INPUTS on (the build refuses
two modules claiming the same SRAM, and a remix's INPUTS is one setting,
not a re-claim). README.md has the design and what was measured per
layout, per direction, and on units.
"""
import dataclasses
import importlib.util
import math
import pathlib

from remix import schema, stock
from remix.schema import (Apply, Category, Claims, Detour, DspHook, DspSection, Gate, Kind,
                          Linked, Module, Option, Poke, Proof, Setting, Store, SymbolRef)

H = bytes.fromhex

# The descriptor generator beside this file, loaded by path.
_spec = importlib.util.spec_from_file_location(
    "usb_descriptors", pathlib.Path(schema.__file__).resolve().parents[2] / "modules/usb/descriptors.py")
descriptors = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(descriptors)

SOURCE = "modules/usb"                       # every linked unit lives in this module's directory
STORE_ID = "octabam.usb"

# LAYOUT's labels in USB_LAYOUT order (the index is the assembler's value);
# OFF is last so the six released values keep their numbers.
LAYOUTS = ("TRACKS MAIN CUE", "TRACKS", "MASTER", "MAIN CUE", "MAIN", "TRACKS POST", "OFF")
INPUTS = ("AB", "CD", "ABCD", "OFF")
CHANNELS = {"AB": 2, "CD": 2, "ABCD": 4}     # host channels per INPUTS value; OFF links no in unit


def layout_inc(layout):
    """The `remix.inc` usbaudio.s includes: USB_LAYOUT (the index of LAYOUTS);
    USB_IN 1 when the remix has INPUTS on (usbaudio.s then answers
    GET_INTERFACE(5) from usbaudio_in.s's in_alt)."""
    def inc(modules):
        usb = modules.get("USB") if isinstance(modules, dict) else None
        usb_in = int((usb.build_values.get("INPUTS") != "OFF") if usb is not None else False)
        return (f"| remix.inc -- usbaudio.s's layout\n    .set USB_LAYOUT, {layout}\n"
                f"    .set USB_IN, {usb_in}\n")
    return inc


_ROOT = pathlib.Path(schema.__file__).resolve().parents[2]
XLV_ADDR, XLV_WORDS = 0x6c00, 256           # X:0x6c00.., indexed by XLV >> 7 (0..254 in use)


def xlv_table(image=None):
    """TRACKS POST: payload A's X:0x6c00..0x6cff as 24-bit words, from the
    user's stock image. Refuses unless they are the first quarter of a sine
    (the curve core 0 applies to the MAIN gain): the image or the parse is
    wrong otherwise, and the stems would be silently mis-scaled."""
    import sys
    sys.path.insert(0, str(_ROOT / "tools/build"))
    import dsp_modmap
    img = image if image is not None else stock.STOCK_IMAGE.read_bytes()
    tag, va, ln = dsp_modmap.PAYLOADS[0]
    assert tag == "A"
    mods, blob = dsp_modmap.modules(img, va, ln)
    for sp, addr, cnt, data in mods:
        if sp == 1 and addr <= XLV_ADDR and XLV_ADDR + XLV_WORDS <= addr + cnt:
            off = data + (XLV_ADDR - addr) * 3
            words = [dsp_modmap.w24(blob, off + 3 * i) for i in range(XLV_WORDS)]
            break
    else:
        raise ValueError("USB TRACKS POST: payload A has no X record over X:0x6c00..0x6cff")
    for i, w in enumerate(words):
        want = round(math.sin(2 * math.pi * i / 1024) * 0x7fffff)
        if abs(w - want) > 64 or (i and w <= words[i - 1]):
            raise ValueError(f"USB TRACKS POST: X:0x{XLV_ADDR + i:04x} = 0x{w:06x} is not the "
                             f"sine core 0's XLV curve reads (expected about 0x{want:06x})")
    return words


def post_inc(modules):
    """TRACKS POST's remix.inc: layout 5, plus the XLV table as a macro the
    data section expands (post_xlv)."""
    words = xlv_table()
    lines = ["| the XLV curve: payload A X:0x6c00..0x6cff from the user's stock image (manifest.py)",
             ".macro POST_XLV_TABLE"]
    for i in range(0, XLV_WORDS, 8):
        lines.append("    .long " + ", ".join(f"0x{w:06x}" for w in words[i:i + 8]))
    lines.append(".endm")
    return layout_inc(LAYOUTS.index("TRACKS POST"))(modules) + "\n".join(lines) + "\n"


def in_inc(channels):
    def inc(modules):
        return f"| remix.inc -- usbaudio_in.s's width\n    .set IN_CHANNELS, {channels}\n"
    return inc


# ---- the linked units, in the order the four modules linked them ------------
# The DRAM units share one link, so this order is the address order of every
# image: USB MIDI's four, then usbaudio, then crossbar, then usbaudio_in.

LINKED_MIDI = (
    # his unit, verbatim: the build re-links it at his zone address and
    # compares with his usb-midi.py's blob (1,124 B, from our stock bytes)
    Linked("usbmidi", f"{SOURCE}/usbmidi.s", cpu="54455", dram=True,
           reference=(0x400d24f0, "6291d91e923145be62719eee56c2ca823d36c2d71ae538550e70b5533d404e60")),
    Linked("usbmidi_rx", f"{SOURCE}/usbmidi_rx.s", cpu="54455", dram=True),
    Linked("usbmidi_clamp", f"{SOURCE}/clamp.s", cpu="54455", dram=True),
    # the four configurations for THIS remix (124 B, 250 B with the audio
    # function, 306 B with the host -> device path too) and the absolute
    # `cfg_len` the clamps read
    Linked("usbmidi_cfg", f"{SOURCE}/cfg.s", cpu="5475", dram=True,
           include=descriptors.remix_inc),
)


# ---- the detour sets --------------------------------------------------------
# USB MIDI's nine sites; the ISR, bus-reset and session-end shims of the old
# USB AUDIO OUT module replace these three in a remix with a LAYOUT (they
# chain to usbmidi_rx_bus_end by symbol, as they did as separate modules).

MIDI_DETOURS = (
    Detour(0x4001d9ca, H("4879400b9868"), "usbmidi_rx", "usbmidi_rx_setcfg_shim",
           "SET_CONFIGURATION body: note the speed, then usbmidi's EP2 bring-up (512-byte packets at high speed)"),
    Detour(0x4001e606, H("2039fc0b01ac"), "usbmidi_rx", "usbmidi_rx_isr_shim",
           "usb_isr UI path: EP2 OUT completions -> decode with FIFO room / re-prime, then usbmidi's EP2 IN kick"),
    Detour(0x40010bc8, H("4fefffec48d7043c"), "usbmidi", "usbmidi_send_shim",
           "midi_send entry: queue the message for the USB encoder", pad_to=8),
    Detour(0x400108b0, H("2f02122f000b"), "usbmidi", "usbmidi_prio_shim",
           "priority (realtime) byte sender: queue the byte for the USB encoder"),
    Detour(0x4001e91c, H("4ebaed9a7040"), "usbmidi_rx", "usbmidi_rx_reset_shim",
           "USBSTS.URI handler: a bus reset takes EP2 down until the next SET_CONFIGURATION"),
    Detour(0x4001e952, H("2039fc0b0140"), "usbmidi_rx", "usbmidi_rx_sessend_shim",
           "OTGSC.BSVIS session end (cable pulled): the same, before USBCMD.RS is cleared"),
    Detour(0x4001daec, H("303946c8ce0c"), "usbmidi", "usbmidi_clrfeat_shim",
           "CLEAR_FEATURE(ENDPOINT_HALT): answer for EP2 instead of stalling"),
    # GET_DESCRIPTOR(CONFIG / OTHER_SPEED): the responder's two hardcoded
    # clamps (moveq #32,d0 / cmpl d2,d0 / bcs +4) become min(wLength, cfg_len)
    Detour(0x4001d858, H("7020b0826504"), "usbmidi_clamp", "usbmidi_clamp1_shim",
           "config responder: clamp the reply to the grown configuration's length"),
    Detour(0x4001d896, H("7020b0826504"), "usbmidi_clamp", "usbmidi_clamp2_shim",
           "other-speed responder: the same clamp"),
)

AUDIO_DETOURS = (
    Detour(0x4001dd04, H("2039fc0b01c4"), "usbaudio", "audio_setiface_shim",
           "SET_INTERFACE: interface 4 alt 1 brings the stream up, alt 0 down; others stock"),
    Detour(0x4001d824, H("4879400e20a1"), "usbaudio", "audio_getiface_shim",
           "GET_INTERFACE: interface 4 reports the alt setting the host asked for"),
    Detour(0x4001de64, H("2039fc0b01c0"), "usbaudio", "audio_ctrl_shim",
           "class requests to the clock source (sample rate CUR/RANGE, validity); the rest STALL as stock"),
    Detour(0x4001e91c, H("4ebaed9a7040"), "usbaudio", "audio_reset_shim",
           "USBSTS.URI handler: bus reset puts the audio interfaces (4, and 5 with INPUTS on) back to alt 0"),
    Detour(0x4001e952, H("2039fc0b0140"), "usbaudio", "audio_sessend_shim",
           "OTGSC.BSVIS session end: the same, before USBCMD.RS is cleared"),
    Detour(0x4001d4b2, H("23d04ec95028"), "usbaudio", "audio_ep0page_shim",
           "usb_ep0_send fills the dTD's buffer page 1 too: a configuration straddling a 4 KB page transmitted truncated"),
    Detour(0x4000d9a0, H("42b946104d4e"), "usbaudio", "audio_frame_shim",
           "frame_isr's last instruction: the per-block producer and the packet builder"),
    Detour(0x4001e606, H("2039fc0b01ac"), "usbaudio", "audio_isr_shim",
           "usb_isr UI path: retire EP3 IN completions, then USB MIDI's shim"),
)

CROSSBAR_DETOUR = (
    Detour(0x4001e030, H("203c08000000"), "usbcrossbar", "crossbar_init_shim",
           "USB controller init: SCM BCR and XBS PRS/CRS for slaves 2 and 4, then the displaced load"),
)

IN_DETOURS = (
    Detour(0x4001dd0a, H("008000400040"), "usbaudio_in", "in_setiface_shim",
           "SET_INTERFACE: interface 5 alt 0/1 records the alt and ACKs, other alts STALL; the rest goes on to stock"),
    Detour(0x40004bc0, H("720113c1fc04801d"), "usbaudio_in", "in_state7_shim",
           "frame transfer state 7: EP3 OUT, the ring, and one more transfer to core 0 at $6320",
           pad_to=8),
    Detour(0x4001de6e, H("23c0fc0b01c0"), "usbaudio_in", "in_ctrl_shim",
           "EP0 stall store: vendor GET 0x56 answers the IN counters instead"),
)

_SHARED = {0x4001e606, 0x4001e91c, 0x4001e952}   # the three sites the audio shims take over from MIDI's
_AUDIO_AT_SITE = {d.site: d for d in AUDIO_DETOURS if d.site in _SHARED}
_AUDIO_EXTRA = tuple(d for d in AUDIO_DETOURS if d.site not in _SHARED)

_PRODUCER = 0x4000d9a0
_PRODUCER_NOTE = {
    "TRACKS MAIN CUE": "the per-block producer (20 channels: tracks, MAIN, CUE; + the sum into the rings) and the packet builder",
    "TRACKS": "the per-block producer (16 channels: the tracks; + the sum into the rings) and the packet builder",
    "MASTER": "the per-block producer (track 8's L/R) and the packet builder",
    "MAIN CUE": "the per-block producer (MAIN L/R + CUE L/R) and the packet builder",
    "MAIN": "the per-block producer (MAIN L/R) and the packet builder",
    "TRACKS POST": "the per-track MAIN gains (every block) and the per-block producer (16 channels: the tracks after their gains; + the sum into the rings) and the packet builder",
}


def _dsp(inputs):
    return DspSection(
        asm=f"{SOURCE}/rx_inject_{inputs.lower()}.asm",
        priority=20,
        payloads=frozenset({"A"}),          # core 0 receives the ESAI
        hooks=(DspHook(0x88, (0x627000, 0x000204), "inject",
                       "frame head: the RX block is written before any reader runs"),),
    )


# The ABCD maxima in every combination with INPUTS on: the build refuses two
# modules claiming the same SRAM, and a remix's INPUTS is one setting, not a
# re-claim (docs/proposals/USB.md phase 1).
CLAIMS = Claims(sram=((0x80007c00, 0x80, "EP3 OUT dTDs"),
                      (0x80007c80, 0x300, "EP3 OUT packet buffers"),
                      (0x80007f80, 0x40, "EP0 reply for vendor 0x56")))

MIDI_GATES = (Gate("tools/verify/verify_usbmidi_rx.py", stage="image"),
              Gate("tools/verify/verify_usbmidi_clock.py", stage="image"),
              Gate("tools/verify/verify_usbmidi_replug.py", stage="image"))
# MAIN/CUE aligned with the tracks (skips without a source project)
GATE_ALIGN = Gate("tools/verify/verify_usb_align.py", remix_arg=False, venv=True, stage="image")
# the stems against core 0's own MAIN, sample by sample, under the port (skips without a source project)
GATE_POST = Gate("tools/verify/verify_usb_post.py", remix_arg=False, venv=True, stage="image")
GATE_IN = Gate("tools/verify/verify_usb_in.py", remix_arg=False, venv=True, stage="image")

POKE_COMPOSITE = Poke(0x400e2004, H("000000"), H("ef0201"),
                      "device descriptor: class/subclass/protocol = interface-association composite")


def _variant(values):
    """LAYOUT and INPUTS -> the units, detours, gates, poke and DSP section
    for that combination (the module's Apply.BUILD settings resolved)."""
    layout = values["LAYOUT"]
    inputs = values["INPUTS"]
    if layout == "OFF" and inputs != "OFF":
        raise ValueError("USB: INPUTS needs a LAYOUT: EP3 IN (the audio stream) is "
                         "EP3 OUT's implicit-feedback source")
    midi_only = layout == "OFF"
    with_in = inputs != "OFF"

    linked = list(LINKED_MIDI)
    if not midi_only:
        inc = post_inc if layout == "TRACKS POST" else layout_inc(LAYOUTS.index(layout))
        linked.append(Linked("usbaudio", f"{SOURCE}/usbaudio.s", cpu="5475", dram=True, include=inc))
    if with_in:
        linked.append(Linked("usbcrossbar", f"{SOURCE}/usbcrossbar.s", cpu="5475", dram=True))
        linked.append(Linked("usbaudio_in", f"{SOURCE}/usbaudio_in.s", cpu="5475", dram=True,
                             include=in_inc(CHANNELS[inputs])))

    detours = list(MIDI_DETOURS)
    if not midi_only:
        detours = [_AUDIO_AT_SITE.get(d.site, d) for d in detours]
        detours += [dataclasses.replace(d, note="frame_isr's last instruction: " + _PRODUCER_NOTE[layout])
                    if d.site == _PRODUCER else d for d in _AUDIO_EXTRA]
    if with_in:
        detours += CROSSBAR_DETOUR + IN_DETOURS

    gates = list(MIDI_GATES)
    if layout == "TRACKS MAIN CUE":
        gates.append(GATE_ALIGN)
    elif layout == "TRACKS POST":
        gates.append(GATE_POST)
    if with_in:
        gates.append(GATE_IN)

    return {
        "linked": tuple(linked),
        "detours": tuple(detours),
        "gates": tuple(gates),
        "pokes": () if midi_only else (POKE_COMPOSITE,),
        "dsp": _dsp(inputs) if with_in else None,
        "claims": CLAIMS if with_in else None,
    }


_DEFAULT_VALUES = {"LAYOUT": LAYOUTS[0], "INPUTS": INPUTS[0]}   # TRACKS MAIN CUE + AB, as the four modules' defaults
_DEFAULT_VARIANT = _variant(_DEFAULT_VALUES)

MODULE = Module(
    name="usb", key="USB", kind=Kind.HYBRID,
    category=Category.MIDI_USB, author="markandrus/octemu", author_url="https://github.com/markandrus/octemu",
    proof=Proof.HARDWARE,
    proof_note="cursory testing on Sam's MKII (owner report, 16 Oct 2026); " "`verify_usb` for every LAYOUT and `verify_usb_in` for every INPUTS under the port; on units: MIDI in/out on Sam's MKII (image 64, 25 Sep 2026), Tim's MKI (OCTATRICK9, 26 Sep 2026) and Ignorato's MKII (OCTABAM21, 9 Oct 2026, transmit after three replugs, macOS and Windows 10), USB clock tempo on Kazeko's MKI (#633, 6 Oct 2026); TRACKS MAIN CUE on Sam's MKII and Tim's MKI, MAIN CUE and the ABCD inject on Bryan T's MKII (build 16, 27 Sep 2026), TRACKS POST on allmyfriendsaresynths's MKII (P3, 5 Oct 2026); the crossbar values at stream-up on Bryan T's MKII (usbin-test 12-16, 26-27 Sep 2026); README.md per layout and direction",
    doc="Class-compliant USB-MIDI in/out plus UAC2 audio to and from the host on the OT's own USB port (markandrus/octemu; the input path and crossbar bryantysinger's; the TRACKS POST layout allmyfriendsaresynths's), by its LAYOUT and INPUTS settings.",
    linked=_DEFAULT_VARIANT["linked"],
    detours=_DEFAULT_VARIANT["detours"],
    pokes=_DEFAULT_VARIANT["pokes"],
    dsp=_DEFAULT_VARIANT["dsp"],
    claims=_DEFAULT_VARIANT["claims"],
    gates=_DEFAULT_VARIANT["gates"],
    # GET_DESCRIPTOR(CONFIG): the responder's four `pea <table>` operands.
    symbol_refs=(
        SymbolRef(0x4001d882, 0x400e201c, "usbmidi_cfg", "cfg_fs", "full-speed configuration"),
        SymbolRef(0x4001d88a, 0x400e203c, "usbmidi_cfg", "cfg_hs", "high-speed configuration"),
        SymbolRef(0x4001d8c0, 0x400e207c, "usbmidi_cfg", "cfg_os_hs", "other-speed (type 7), 512-byte EPs"),
        SymbolRef(0x4001d8c8, 0x400e205c, "usbmidi_cfg", "cfg_os_fs", "other-speed (type 7), 64-byte EPs"),
    ),
    store=Store(STORE_ID),
    settings=(Setting(1, "LAYOUT", Option(*LAYOUTS), default="TRACKS MAIN CUE", apply=Apply.BUILD,
                      doc="which channels go to the host: the six layouts above, or OFF for USB MIDI alone"),
              Setting(2, "INPUTS", Option(*INPUTS), default="AB", apply=Apply.BUILD,
                      doc="which inputs the host's channels stand in for (AB, CD, ABCD), or OFF for no host -> device stream")),
    variant=_variant,
)
