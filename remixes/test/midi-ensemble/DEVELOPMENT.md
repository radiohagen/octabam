# MIDI ensemble verification carrier

Scales, Follow and Harmony beside STORE, KITS, MIDI SCENES, SCENES P2,
PLOCKS P2, MIDI PART STATE, MIDI SRAM and HARMONY PLOCKS. Audio effects
stay stock. It exercises the same MIDI/persistence composition as the personal
BottleService carrier without requiring its audio rig or USB layout.

Build/check: `make check REMIX=midi-ensemble`. With a prepared project, run
`verify_harmony_degree_kits_port.py --project DIR --scenes --size-four`,
`verify_harmony_size_scenes_port.py --project DIR`, and
`verify_harmony_track_port.py --project DIR` against a frozen image.
These are emulator checks. Physical boot, timing and retained-state acceptance
are separate; this carrier is not a boot fix.
