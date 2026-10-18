A mono single-head tape echo with stereo dry output, in place of FX2
SPRING REV. It runs on the ColdFire CPU, not the DSP, in the stock delay's
four-second per-track ring, so the DSP side is an empty passthrough.
Repeats darken and wobble with the AGE and WOW knobs, and feedback past the
middle grows tape noise into self-oscillation.

## Access

An effect on a track: select the track, press FX2, and pick TAPE ECHO from
the chooser, where SPRING REV was. Everything is on page 1; page 2 is
disabled. Not in an official remix; build the test remix `tapeecho`.
Not hardware-qualified: earlier builds froze the unit while editing with
three to six instances, and the current build is not flashed.

![FX2 SETUP with Tape Echo selected.](../../img/tapeecho/chooser.png)

*FX2 SETUP with Tape Echo selected.*

## Operation

- SYNC FREE: TIME is continuous, 46 to 231 ms.
- SYNC BEAT: TIME picks one of twelve note divisions, shown by name
  (T = triplet, dot = dotted): 1/64, 1/32 triplet, 1/32, 1/16 triplet,
  1/16, 1/8 triplet, dotted 1/16, 1/8, 1/4 triplet, dotted 1/8, 1/4,
  dotted 1/4. The time follows the project tempo; all twelve fit from 30 to
  300 BPM.
- A change of delay time in BEAT crossfades the read for about 11.6 ms and
  settles within about 23 ms of the last edit.
- MIX 0 is exact dry.
- DRIVE is fixed at 0.
- AGE sits in the slot HEADS had. A saved project that used HEADS locks
  needs them reset.

## Parameters

| Page | Knob | Range | What it does |
|---|---|---|---|
| 1 | TIME | 0-127 | 46-231 ms in FREE; a division in BEAT |
| 1 | FDBK | 0-127 | regeneration; the top of the range self-oscillates |
| 1 | WOW | 0-127 | 0.8 Hz wow plus random flutter; 0 is static |
| 1 | AGE | 0-127 | repeat bandwidth, flutter and hiss; fresh at 0, worn at 127 |
| 1 | SYNC | FREE, BEAT | continuous or tempo-quantised time |
| 1 | MIX | 0-127 | dry/wet; 0 is exact dry |
