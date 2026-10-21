# MIDI Loopback / MIDI Scenes bridge

Routes MIDI Scenes output through each source track's Loopback DEST, using
the Part that Scenes is mixing. Select it when combining **MIDI Loopback**,
**MIDI Scenes** and USB MIDI support. It adds no controls.

- EXT sends Scene output externally.
- INT sends it to the internal receiver.
- BOTH sends one copy to each destination.

Scene CCs keep their order before note-on. Other DIN/USB callers keep their
normal behavior. Audio CC Feedback is a separate path; set **AUDIO CC OUT =
INT** when that feedback should also stay internal.

[Producer boundaries, integration and verification](DEVELOPMENT.md).
