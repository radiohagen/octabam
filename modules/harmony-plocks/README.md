# Harmony / PLOCKS P2 bridge

Allows **MIDI Harmony** and **PLOCKS P2** to share editing and copy operations.
Select **HARMONY PLOCKS** with both modules and their normal dependencies.
It adds no controls.

- Held-step editing uses Harmony on MIDI tracks and PLOCKS P2 on audio tracks.
- Both sets of locks follow native pattern/track copy, clear and undo.
- STORE coordinates project operations. A failed Harmony companion save
  prevents the associated native bank and companion backup writes.

The bridge allocates no retained memory. With Harmony **MIDI TRACK**, Harmony
uses [MIDI SRAM](../midi-sram/README.md); PLOCKS retains its separate capacity
of 4,768 unsaved locks. Project companions remain P2LK v1 and HDP3.

[Shared hooks, storage boundaries and verification](DEVELOPMENT.md).
