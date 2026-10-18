A Euclidean fill for sample trigs. Hold a TRACK key and press PAGE, and a
window opens (title and target tracks, STEPS, PULSE, ROT, and a live
pattern bar). YES writes the rhythm onto the held tracks' sample-trig
mask.

This edits sequencer trigs; it is not the DSP EUCLID effect, which
modulates filter or amplitude. It leaves PROJECT > CONTROL > SEQUENCER
alone, so it coexists with SCALE QUANTIZER.

## Access

Hold a TRACK key and press PAGE. Targets are the track keys held when the
window opened; with none held, the current audio track. TRACK + PAGE again
closes it, as does NO. FUNC + PAGE (SCALE SETUP) and PAGE alone stay stock.
Not in an official remix; build the test remix `euclid-fill`.
Hardware: cursory testing on Sam's MKII (owner report, 16 Oct 2026).

## Operation

- STEPS is the pattern length (with PER TRACK, the first target track's
  length). It is shown, not edited.
- PULSE defaults to 5 and ROT to 0; they are not saved.
- YES writes the Euclidean trigs on the targets, NO closes.

## Controls

| Control | Does |
|---|---|
| TRACK + PAGE | open / close |
| UP / DOWN | move the cursor between PULSE and ROT |
| LEFT / RIGHT | step the focused value by 1 |
| A | PULSE |
| B | ROT |
| LEVEL | turn the focused value |
| YES | write the trigs on the targets |
| NO | close |
