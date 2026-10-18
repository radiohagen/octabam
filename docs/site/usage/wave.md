A 4-voice wavetable synth on FX2, on the DSP, ported from CHOMPI WAVE's
voice (wavetable oscillator, DJ filter, filter and pitch LFOs). It is
played by the track it sits on: the track plays a sine (the carrier), WAVE
measures the carrier's pitch and level, and its four voices follow them.
PTCH, the CHROMATIC keys, SCALE QUANTIZER, p-locks, LFOs on PTCH and the
AMP envelope all play it. It is an experiment.

## Access

1. Write the carrier with the module's `carrier.py WAVCAR.wav`: a C5 sine,
   2,093 whole cycles in 4 s, so it loops without a seam. Put it in the
   set's audio pool.
2. On a FLEX track, load WAVCAR.wav with loop on. Press FX2 and pick
   **Wave Synth**. The track's own audio is replaced by the synth.
3. Play with trigs, PTCH or the CHROMATIC keys. The voices play the
   carrier's note OCT octaves down (default -2: PTCH 0 is C3). The AMP
   envelope is the synth's envelope; with loop on and AMP REL at INF it
   holds until the envelope ends it.

Not in an official remix; build the test remix `wave`, which takes DARK
REV's and SPRING REV's words, so both reverbs are off its chooser. The
first 23 ms after the effect starts are silent while it writes its tables.

![FX2 SETUP with Wave Synth selected: FDEP, FRAT, VDEP, VRAT and DETN on its page 2.](../../img/wave/chooser.png)

*FX2 SETUP with Wave Synth selected: FDEP, FRAT, VDEP, VRAT and DETN on its page 2.*

## Operation

- FRAM morphs through sine, triangle, saw, square and pulses 1/4 to 1/32.
- CUT is a DJ filter: low-pass below the middle, high-pass above.
- CHRD sets the four voices' intervals over the note: UNI, OCT, 5TH, MAJ,
  MIN, MAJ7, MIN7, SUS4. The intervals are fixed; SCALE QUANTIZER snaps the
  played note, not the chord's other voices.
- FDEP/FRAT drive a filter LFO; VDEP/VRAT a vibrato of up to +-2
  semitones; DETN spreads the voices up to +-60 cents on the outer two.
- Two or three WAVE tracks per core fit beside light effects; four do not.
  How many fit on the unit is not measured.

## Parameters

| Page | Knob | Range | What it does |
|---|---|---|---|
| 1 | FRAM | 0-127, default 0 | wavetable position |
| 1 | CUT | 0-127, default 80 | DJ filter |
| 1 | RES | 0-127, default 40 | resonance |
| 1 | CHRD | 8 shapes | the voices' intervals |
| 1 | OCT | -4..0, default -2 | octaves below the carrier |
| 1 | LEVL | 0-127, default 64 | output level |
| 2 | FDEP | 0-127, default 0 | filter LFO depth |
| 2 | FRAT | 16 steps, 0.14-65 Hz | filter LFO rate |
| 2 | VDEP | 0-127, default 0 | vibrato depth |
| 2 | VRAT | 16 steps, 0.14-65 Hz | vibrato rate |
| 2 | DETN | 0-127, default 0 | voice spread |

Heard working on a MKII on 3 Oct 2026: it plays, and PTCH and the
CHROMATIC keys move the pitch.
