# `usb-out-tracks` — USB LAYOUT TRACKS on the stock effects

The stock chooser plus USB at LAYOUT TRACKS, for testing the sixteen-channel stream on a unit that runs stock projects: no FX1 stations, no chooser changes, no project stamping.

## What is in it

- **USB** (markandrus/octemu) at LAYOUT TRACKS: USB-MIDI mirroring DIN; sixteen 24-bit channels, track N's L/R on 2N−1/2N, post-FX, pre-fader; the tracks' stereo sum at full speed. [`USB`](../../../modules/usb/README.md#tracks).
- the 14 stock FX2 effects.

## Status

Port only (`verify_usb`, 27 Sep 2026). Image 69 (Sam's MKII, 25 Sep 2026) ran sixteen channels at 24 bits from the source as it was before MAIN/CUE; this build is the current source with MAIN/CUE left out, and has not run on a unit.

## Build

```bash
make image REMIX=usb-out-tracks BUILD=1   # -> out/OCTATRACK_OCTABAM1.bin
```

[BUILDING.md](../../../docs/guide/BUILDING.md) is the walk-through from a fresh machine to a flashed unit. `make check REMIX=usb-out-tracks` runs every gate first.
