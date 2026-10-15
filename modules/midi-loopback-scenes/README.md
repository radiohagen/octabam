# MIDI Loopback / MIDI Scenes bridge

Required in the integrated USB remix when MIDI Loopback and MIDI Scenes are
selected together. MIDI Scenes replaces the sequencer CC loop and emits scene
changes through the native control sender. The bridge routes those messages
using the source track's DEST in the Part that MIDI Scenes is actually mixing.

The sequencer CC sender is identified at the common sender entry before USB
MIDI mirrors it; all other callers continue through the unchanged USB/DIN
sender. The Loopback control adapter recognizes the Scene mixer's caller.
There is no global origin flag and no change to MIDI Scenes or KITS source.

The bridge pins the MIDI Scenes source hash and checks its context offsets
and producer boundaries. Updating MIDI Scenes requires re-auditing that pin.
EXT preserves Scene output; INT stays internal; BOTH delivers one of each.
Scene CCs retain MIDI Scenes' intentional order before note-on.

CC Feedback remains a separate audio output path. Use AUDIO CC OUT = INT
when audio-control feedback should stay internal too. Combined routing tests
use this setting and retain the complete MIDI capture, while checking every
message after transport starts. These are emulator checks, not hardware proof.
