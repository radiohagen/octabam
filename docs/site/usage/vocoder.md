A ten-band channel vocoder after the Roland VP-330: the track's audio (a
voice) shapes a carrier, built in or external. The output is mono on both
channels.

## Access

An effect on a track: select the track, press FX2, and pick VOCODER.
**It runs on FX2 of tracks 2, 3, 6 and 7 only.** On tracks 1, 4, 5 and 8,
and on any FX1 slot, it passes audio through untouched. Two VOCODERs per
DSP core play (tracks 1-4 share one core, 5-8 the other); a third on a core
stays dry instead of overrunning it. Not in an official remix; build the
test remix `vocoder`.

Heard on a MKII on 4-5 Oct 2026, by ear: it plays and is intelligible, and
one or two per core ran clean. Left-only click bursts on T1 were measured,
which is why T1 and T5 are excluded.

![FX2 SETUP with VOCODER selected: MODE INT.](../../img/vocoder/chooser.png)

*FX2 SETUP with VOCODER selected: MODE INT.*

## Operation

- MODE INT: the carrier is built in, two sawtooths an octave apart at
  NOTE. Turn NOTE, or parameter-lock it on the steps, and the vocoded voice
  plays a melody. Play a voice, sample or live input through a THRU
  machine.
- MODE EXT: the carrier is the track's right channel, for example a THRU
  track with the voice on input A and a synth on input B. The modulator is
  the left channel; in INT it is left and right averaged.
- CONS passes the voice above 4 kHz, as the VP-330's high-consonant
  circuit does.
- A saved NOTE above C6 plays C6.
- The VP-330's ensemble chorus is not modelled.

## Parameters

| Page | Knob | Range | What it does |
|---|---|---|---|
| 1 | NOTE | C1..C6 | the built-in carrier's pitch; default C3 |
| 1 | CONS | 0-127 | consonants: the voice above 4 kHz passed through; default 48 |
| 1 | DRY | 0-127 | the dry voice mixed in; default 0 |
| 1 | LEVL | 0-127 | output level; 127 is unity, default 100 |
| 2 | MODE | INT, EXT | the carrier |
