# Harmony MIDI bus

Combines the Octabam bus with MIDI Scales, Follow, Harmony and Loopback,
plus Part State, STORE and the bridges for KITS, Scenes and PLOCKS.

Harmony uses **MIDI TRACK** retention: each MIDI step holds its own degree/chord
token and accumulator amount. Track clear removes its locks; copy, paste and undo carry the musical
data. PLOCKS retains its separate 4,768-lock capacity, and MIDI Scenes retains
its own 16,384-byte store.

Keep the Harmony `hdeg*.work` / `hdeg*.strd` and P2LK companion files with the project.
Use a separate project copy for stock firmware, which does not interpret
Harmony's degree/chord storage or preserve all additional Part settings.

See [Harmony](../../modules/midi-harmony/README.md),
[Follow](../../modules/midi-follow/README.md) and
[Loopback](../../modules/midi-loopback/README.md) for controls.

[Developer notes and verification](DEVELOPMENT.md).
