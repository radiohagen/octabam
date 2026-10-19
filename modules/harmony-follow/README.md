# Harmony / Follow bridge

Select **HARMONY FOLLOW** when MIDI Harmony and MIDI Follow are both selected.
It gives both modules one transport and successful-note dispatcher, so register
history and the Harmony accumulator receive each event once. Harmony and Follow
also work independently, without this bridge. It adds no controls or storage.

A source with HARM OFF supplies its effective N1–4 pitches. A source with HARM
NOTE or CHORD supplies only its resolved degree:oct root as Note 1. A follower
with HARM OFF plays that supplied set; a follower with HARM NOTE or CHORD uses
the supplied root to generate its own notes. The source's generated chord voices
are never copied. An absent Harmony module behaves like HARM OFF.

The installed-hook accumulator gate checks transport, note-on success, rejected
output and live-arp guards. The Follow note gate checks all source/follower HARM
modes. These are software checks; hardware acceptance is separate.

Run the full firmware matrix with
`tools/verify/verify_harmony_follow_port.py --project DIR`. It copies its input,
tests all nine source/follower mode pairs with both earlier and later source
tracks, and checks complete UART pitch sequences plus balanced releases. With
Harmony absent, it checks native four-note Follow in both source orders.
