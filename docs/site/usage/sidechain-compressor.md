The stock COMPRESSOR with a side-chain: any of tracks 1-8 can drive its
detector, so one track's level ducks another. Page 2 adds the key and its
filter and gain, and a switch to listen to the key.

## Access

An effect on a track: select the track, press FX2, and pick
COMPRESSOR from the chooser; the setup page shows the new knobs. Not in an
official remix; build the test remix `sidechain-compressor` (or
`kyoti-mute-sidechain`). It uses SPRING REV's words, so SPRING REV is off
the chooser in those images. It does not coexist with BusDelay or BusVerb:
their core-private and cross-core memory overlaps, and the build refuses
the pair.

![FX2 SETUP with COMPRESSOR selected, showing RMS, KFLT, KGN, KEY and MON.](../../img/sidechain-compressor/chooser.png)

*FX2 SETUP with COMPRESSOR selected, showing RMS, KFLT, KGN, KEY and MON.*

## Operation

- KEY chooses what drives the detector: OFF (the track's own signal, as
  stock) or T1-T8.
- KFLT filters the key before it is detected: 64 is bypass, below 64 is a
  low-pass, above 64 a high-pass.
- KGN is the key's gain, about -24 to +24 dB.
- MON lets you hear the processed key in place of the track.
- A COMPRESSOR saved on stock firmware comes up with KEY OFF, KFLT and KGN
  centred and MON OFF.
- The key works across the two DSP cores in both directions (T1 to T5 and
  T5 to T1 were tested).
- A muted key track still ducks, in every MUTE MODE.
- RMS stays beside it as on stock.

## Parameters

| Page | Knob | What it does |
|---|---|---|
| 1 | stock COMPRESSOR | as stock |
| 2 | RMS | stock's |
| 2 | KEY | OFF or T1-T8 |
| 2 | KFLT | key filter: 64 bypass, below low-pass, above high-pass |
| 2 | KGN | key gain, about -24 to +24 dB |
| 2 | MON | hear the processed key |

Tested on the author's MKI on 4 Oct 2026 with ducking, KFLT, KGN, MON and
cross-core keys.
