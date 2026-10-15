# MIDI Scenes integration

Harmony adapts the upstream MIDI SCENES public `scn_slot_ptr`,
`scn_slot_changed` and `scn_invalidate` interfaces. KITS and MIDI SCENES source
remain unchanged. The old MIDISC2.1 sparse-table and stack-workaround adapter
is removed; the current module owns full 4,096-byte Part tables.

With HARM NOTE/CHORD, scene NOTE endpoints are DEG (0..83). The crossfader
interpolates degree codes and Harmony resolves the result through the
captured track's effective KEY. Empty endpoints inherit the current root.
Changing KEY preserves degree identity. Explicit HARM OFF converts endpoints
to native NOTE; switching on encodes against the effective KEY. NOTE/CHORD
changes preserve degrees. CHRD and dormant native NOT2–4 remain outside
scene-root editing. Other scene parameters retain upstream behavior.

Before a native Part replacement, the shared MIDI PART STATE boundary takes
an outgoing snapshot of its scene assignments and 128 NOTE endpoints.
Readers use that snapshot while the native Part is being copied. The previous
32-active-parameter limit no longer applies. Upstream owns table persistence,
Part/Kit copies and ordinary MIDI morphing. Integration gates must verify
these interactions on the combined carrier; a build alone is insufficient.
