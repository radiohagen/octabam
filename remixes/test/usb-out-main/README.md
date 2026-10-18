# `usb-out-main` — USB LAYOUT MAIN on the stock effects

The stock chooser plus USB at LAYOUT MAIN, for testing the
two-channel MAIN stream on a unit that runs stock projects: no FX1
stations, no chooser changes, no project stamping.

## What is in it

- **USB** at LAYOUT MAIN (markandrus/octemu's source; the
  MAIN layout ours): USB-MIDI mirroring DIN; MAIN L/R to the host, 24-bit,
  every 250 µs at high speed, every 1 ms at full speed.
  [`USB`](../../../modules/usb/README.md#main).
- the 14 stock FX2 effects.

## Status

Port only (`verify_usb`, 28 Sep 2026). Not on a unit. `usb-io-main-ab` is
this plus INPUTS AB (and the crossbar USB always sets): a two-in, two-out interface.

```
make image REMIX=usb-out-main BUILD=1   # -> out/OCTATRACK_OCTABAM1.bin
```

[BUILDING.md](../../../docs/guide/BUILDING.md) is the walk-through from a
fresh machine to a flashed unit. `make check REMIX=usb-out-main` runs every
gate first.
