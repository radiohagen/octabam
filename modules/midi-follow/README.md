# MIDI Follow

Makes one MIDI track follow another track's root notes while keeping its own
rhythm, velocity and note length. Use it for a bassline that follows a chord progression.

## Use

1. On the follower, open **NOTE SETUP** with **FUNC + SRC**.
2. Turn **D: RFOL** from OFF to the source track, for example T1.
3. Program the source's notes and the follower's rhythm. Give them separate
   output channels; start with the follower's arp off.
4. Press D to open **FOLLOW**. Set MODE, OCT and UPDT.

| Control | Behavior |
| --- | --- |
| MODE: FIXED | Uses the source pitch class in OCT 0–10; default octave 3. |
| MODE: SOURCE | Uses the source's full root pitch, shifted by OCT -2 to +2. |
| UPDT: TRIG | Takes the latest root at the follower's next programmed note. |
| UPDT: LIVE | Also updates a held follower note when the source root changes. |

Each mode remembers its own OCT setting. Octave names use C0 = MIDI 0.
Use the follower's native **TRAN**, including parameter locks, for a semitone
offset after register selection. TRAN +7 is always seven semitones, not a scale degree.
Out-of-range roots are silent.

## Musical behavior

- RFOL OFF uses native notes. Before a source root is available, playback is unchanged.
- A source chord or arp supplies its root, not each generated tone. A follower
  without Harmony plays one root and suppresses NOTE2–4.
- Several tracks can follow one source. Chains use the ultimate source and
  the final follower's settings; intermediate transpositions do not accumulate.
  The selector prevents self-following and cycles.
- Source rests retain the last root. Muting the source silences its output but
  lets its root progression continue driving followers.
- Same-tick source trigs are captured before followers play. An earlier
  microtimed follower trig uses the preceding root.
- With Harmony, the follower keeps its own chord shape and voicing. It inherits
  the source's effective KEY; that KEY is read-only on the follower.

## Storage and stock firmware

RFOL, MODE, both OCT choices and UPDT are native Part settings per track.
Runtime roots and held notes are not saved. Requires **MIDI Part State**;
Harmony, Scales and KITS are optional.

Stock 1.40C preserves the source-track number but resets the mode, response
and octave fields. After saving that bank on stock, Follow returns as **FIXED,
octave 0, TRIG**, with a remembered SOURCE offset of **-2 octaves**. Keep a
separate project copy to preserve these settings.

[Detailed behavior, implementation and verification](DEVELOPMENT.md).
