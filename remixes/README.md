# Remixes

A remix is a named selection of modules; `make image REMIX=<name> BUILD=<n>` builds it into a card-flashable image from your own OS 1.40C. Each remix is a directory here: `remix.py` is the selection, `README.md` says what is in it, where it has run and how to flash it. This index is rendered from the selections (`make docs`).

- What to install first (the Xcode Command Line Tools, Homebrew, Python 3.10+, `cmake`, `uv`) and every step to a flashed unit: [BUILDING.md](../docs/guide/BUILDING.md).
- Composing your own: [REMIXER.md](../docs/guide/REMIXER.md).
- The remixes that carry one module for its gates: [test/](test/README.md).

## The delay and reverb bus

| remix | contains | proof |
|---|---|---|
| [`harmony-track-bus`](harmony-track-bus/README.md) | Bus with Scales, Follow, Harmony and Loopback; Harmony retained per MIDI step; upstream PLOCKS. | `make check`: Experimental track-local retention; hardware untested. |
| [`octabam-bus`](octabam-bus/README.md) | CORE + the delay and reverb bus (BusDelay on T1's FX2, BusVerb on T5's FX2, SEND on every other track's FX2, the stock DELAY on T8) + SPECTRUM, CHARACTER and MODULATION on FX1. | port-gated |

## Firmware mods on the stock effects

| remix | contains | proof |
|---|---|---|
| [`octabam-core`](octabam-core/README.md) | The core ColdFire modules on the 14 stock effects, with LOFI AMF FIX. | port-gated |
| [`octabam-inserts`](octabam-inserts/README.md) | CORE + SPECTRUM, CHARACTER, MODULATION, TRANSIENT and EUCLID on FX1 and FX2, LOFI2 (FX2), the stock DELAY and GATE VERB on FX2. | port-gated |

Never share a built image: it contains Elektron's OS.
