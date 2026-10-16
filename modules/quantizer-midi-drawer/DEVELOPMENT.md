# Quantizer MIDI Drawer

Compatibility bridge for SCALE QUANTIZER. The native MIDI chromatic drawer
branches from `0x400449b6` into the value push at `0x400449be`. The quantizer's
audio octave detour spans `0x400449b8..0x400449bf`, replacing that push with
padding. The MIDI path therefore omits one formatter argument, and the later
stack cleanup consumes a saved register. A full-firmware emulator run then
returns into low memory before transport can start.

This bridge intercepts the MIDI-only load at `0x400449ae`, replays its native
`octave - 1` computation and stack push, and rejoins the formatter at
`0x400449c0`. The quantizer's audio/synth branch and pinned author source stay
unchanged. No persistence or UI control changes.

`verify_quantizer_midi_drawer.py` executes the installed hook, pristine stock
as the oracle, and the unbridged quantizer as a negative control across all
native MIDI octaves. It checks the value, stack and preserved registers.
Full-firmware synth/bus and MIDI screen checks qualify the combined remix.
Hardware behavior is unverified.
