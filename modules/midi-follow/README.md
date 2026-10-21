# MIDI Follow

Makes one MIDI track follow another track's notes while keeping its own
rhythm, velocity and note length. It can copy a native four-note chord or
provide a root for the follower's own Harmony arrangement.

## Use

1. On the follower, open **NOTE SETUP** with **FUNC + SRC**.
2. Turn **D: RFOL** from OFF to the source track, for example T1.
3. Program the source's notes and the follower's rhythm. Give them separate
   output channels; start with the follower's arp off.
4. Press D to open **FOLLOW**. A/B/C are **RFOL**, **REG**, **OCT/OFFS**;
   D is **UPDT**. E/F do nothing. Stock dials and switches show the values.

| Control | Behavior |
| --- | --- |
| REG: FIXED | Uses the source pitch class in OCT 0–10; default octave 3. |
| REG: GRAV | Ignores source octave; balances small movements with a preference for OCT 0–10. Default octave 3. |
| REG: SOURCE | Uses the source's full root pitch, shifted by OFFS −2 to +2. Default 0. |
| UPDT: TRIG | Takes the latest logical source notes at the follower's next programmed note. |
| UPDT: LIVE | Also shifts held follower notes when the source root changes. |

Each mode remembers its own value in the same C control. FIXED is the default;
RFOL starts OFF and UPDT starts TRIG. Octave names use C0 = MIDI 0.
Use the follower's native **TRAN**, including parameter locks, for a semitone
offset after register selection. TRAN +7 is always seven semitones, not a scale degree.
Out-of-range roots are silent.

GRAV prefers the twelve notes C–B in the selected octave without a hard
register boundary. At OCT2, B2 → C can become B2 → C3 instead of jumping to
C2; a following F returns to F2. It can still make larger return jumps.
Its reference is the previous successfully played Follow root, before Harmony
ACC and TRAN. Chord voices, repeated arp output and display reads do not
advance that reference. The first root starts in the preferred octave (or
the closest valid octave for the partial OCT10). Transport start/resume,
Part replacement/change and source/register/home edits reset the reference;
ordinary pattern changes alone retain it.

## Musical behavior

- RFOL OFF uses native notes. Before a source root is available, playback is unchanged.
- With HARM OFF on the source, its effective NOTE and NOT2–4 form the followed
  note set. A follower with HARM OFF (or no Harmony module) plays that set in
  its selected register, with its own TRAN. Its stored NOT2–4 do not add notes.
- With HARM NOTE or CHORD on the source, only its resolved `degree:oct` root
  is followed. Generated source chord and arp tones are not copied.
- With HARM NOTE or CHORD on the follower, Harmony uses the followed root and
  generates that track's own notes, quality and voicing.
- LIVE shifts currently held notes when the source root moves. A change to
  native NOT2–4 with the same root takes effect at the follower's next trig.
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

RFOL, REG, all three remembered values and UPDT are native Part settings per track.
Runtime roots and held notes are not saved. Requires **MIDI Part State**;
Harmony, Scales and KITS are optional. The greenfield packed format reuses
the existing Follow fields; no additional persistent bytes or step data.
Select **SEQUENCER EVENTS** for transport and accepted-output notifications.
Follow and EUCLID register independently with this platform and can be selected together.
Re-enter register settings from an earlier Follow build; there is no migration.

Stock 1.40C preserves the source-track number but resets the mode, response
and octave fields. After saving that bank on stock, Follow returns as **FIXED,
octave 0, TRIG**, with a remembered SOURCE offset of **-2 octaves**. Keep a
separate project copy to preserve these settings.

## Verification and limits

Measured in the ColdFire emulator: native one-to-four-note following,
register and TRAN behavior, source order, mute handling, LIVE updates,
Part changes and balanced note releases. The linked-code gates also check
cycle rejection, register preservation and bounded memory writes.

Physical MIDI timing and behavior on an MKI/MKII remain unverified. The
emulator results support an expectation of matching device behavior; they
do not establish it. No hardware flash or acceptance is claimed.

[Detailed behavior, implementation and verification](DEVELOPMENT.md).
