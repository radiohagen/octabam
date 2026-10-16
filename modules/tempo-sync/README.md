# TEMPO SYNC

Displays BusDelay's TIME as a tempo division while its tempo snap is active,
and in milliseconds otherwise. It also passes each track's held MIDI note to
BusDelay. There are no additional controls.

BusDelay reads the native project tempo. Held-note input applies only to tracks
using BusDelay in FX2; releasing the note clears that input.

The `CAVE` build setting provides two diagnostic modes:

- **OFF:** no note hook or division formatter; TIME displays milliseconds.
- **REPLAY:** keeps the hook but only replays the native instructions.

[Implementation, diagnostic builds and verification](DEVELOPMENT.md).
