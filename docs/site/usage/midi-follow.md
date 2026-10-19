MIDI Follow lets a MIDI track play another track's notes at its own rhythm,
velocity and note length. It uses the source's native N1–4 pitches and keeps
their intervals when placing them in the follower's register. Several tracks
can follow one source; chains resolve to their final source.

## How to Use It

1. Program notes on a source MIDI track and trigs on a follower track.
2. On the follower, open **NOTE SETUP** with **FUNC + SRC**.
3. Turn **D: RFOL** to the source track, then press D to open **FOLLOW**.
4. Set **REG** to FIXED (pitch class in **OCT**), GRAV (nearby notes around
   **OCT**), or SOURCE (source octave plus **OFFS** of −2 to +2).
5. Set **UPDT** to TRIG for changes at the follower's next trig, or LIVE to
   shift held notes when the source root changes.

The follower's **TRAN** adds a chromatic semitone offset after register
placement. Its stored N2–4 do not add notes: when the source has N2–4, those
source voices are followed even if the follower's own slots are empty. A
source rest retains the last notes. Source mute silences its output while
allowing its notes to drive followers. Give source and follower separate MIDI
channels while checking the result.

## Storage and Composition

RFOL, register choices and UPDT live in each native Part. Fresh Parts default
to RFOL OFF, FIXED octave 3 and TRIG. Select **MIDI PART STATE** with Follow;
the standalone test remix does so. Harmony is optional. With Harmony NOTE or
CHORD on the source, only its resolved degree:oct root is followed. With
Harmony NOTE or CHORD on the follower, that track generates its own chord
from the followed root. The combined Harmony image needs the separate MIDI
Part State to MIDI SRAM long-branch fix before it can link.
EUCLID uses Follow's transport start/resume sites, so that combination needs
a shared-hook bridge and is currently refused.

Stock 1.40C loads the source-track number but resets Follow's mode, response
and octave fields when saving the bank. Keep a project backup before returning
to stock. This module has emulator MIDI-output checks; hardware behavior has
not been verified.
