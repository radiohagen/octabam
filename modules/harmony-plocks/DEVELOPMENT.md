# Harmony / PLOCKS P2 bridge

Select `HARMONY PLOCKS` alongside `MIDI HARMONY`, `PLOCKS P2` and their
normal dependencies. It adds no player control.

The bridge owns the shared audio/MIDI editing and pattern/track copy sites.
The held-step encoder dispatches to Harmony on MIDI tracks and P2 on audio
tracks; both independent mirrors accompany native copies.

Harmony is a registered STORE client alongside P2, KITS and MIDI SCENES.
STORE owns every shared persistence hook; Harmony has no STORE overrides
or native load/new-project call-site patches. A failed Harmony companion save blocks the native bank and
companion backup copies. Each native operation executes once.

The bridge allocates no retained memory. The experimental `harmony-track-bus`
carrier uses Harmony `MIDI TRACK`, with each retained token at its matching
MIDI step, and upstream PLOCKS P2 storage (4,768 unsaved retained locks). The separate
PLOCKS editor correction changes no retained allocation.
Neither PLOCKS nor MIDI Scenes changes its reservation. See
[MIDI SRAM](../midi-sram/README.md) and
[Harmony layout](../midi-harmony/degrees/README.md).
Project companion formats remain P2LK v1 and HDP3.

`tools/verify/verify_harmony_plocks.py` exercises capacity, copy/undo,
companion I/O, error guards and reset with substituted filesystem boundaries. The registered packed-storage gate
dispatches to track-retention checks when MIDI TRACK is selected: all legal
tokens, corruption, scoped clear/restore and interrupted checkpoints.
`tools/verify/verify_harmony_track_port.py` runs the actual firmware
with all three retained stores at capacity through checkpoint, clear and restart.
The musical Kit/Scenes port gates cover recall, editor gestures and release
ownership. Emulator evidence does not establish physical battery retention
or hardware acceptance.

## Build and verify

`make check REMIX=harmony-plocks` exercises the bridge on stock audio effects.
For the complete protected-pool composition, use the integrated carrier and
run its retained-capacity and MIDI/Scenes/KITS interaction gates. A passing
hook ledger alone does not establish behavior when both editors are active.
