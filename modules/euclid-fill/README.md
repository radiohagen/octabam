# `euclid-fill` — EUCLID FILL

A standalone Euclidean **sample-trig** fill page. Hold a **TRACK** key and
press **PAGE**: a TUNER-style window opens (title + target tracks, STEPS /
PULSE / ROT, live pattern bar). STEPS is the pattern length (PER TRACK: the
first target track's length). **YES** writes the rhythm onto the held
track(s)' sample-trig mask; **NO** or TRACK+PAGE again closes.

Not the DSP [EUCLID](../euclid/README.md) effect (filter/amp modulation).
This module only edits sequencer trigs. It does not grow
`PROJECT > CONTROL > SEQUENCER`, so it coexists with SCALE QUANTIZER.

Rhythm names, ranges, and the PULSE default match filter EUCLID; STEPS is
sourced from pattern length instead of a stored knob. Encoder **A** turns
PULSE and **B** turns ROT (same input-layer pattern as TEMPO BUS).

## Controls

| control | does |
|---|---|
| TRACK + PAGE | open / close |
| UP / DOWN | move the cursor (PULSE ↔ ROT) |
| LEFT / RIGHT | step the focused value by 1 |
| A | PULSE (focus follows) |
| B | ROT (focus follows) |
| LEVEL | turn the focused value (signed detents) |
| YES | write Euclidean trigs on the targets |
| NO | close |

Targets are the track keys held when the window opened. If none were
held, the current audio track is used. **STEPS is the pattern length**
(SCALE SETUP; PER TRACK: first target track's length) — shown, not
edited. PULSE defaults to 5, ROT to 0 (DRAM, not saved).

FUNC + PAGE (SCALE SETUP) and PAGE alone stay stock.

## Measured

- Not yet: the fill writer follows the bank-blob + battery-mirror + dirty
  recipe from ERASE_EMPTY_TRIGLESS_LOCKS; the window stack follows TUNER.
- `make check REMIX=euclid-fill` builds and boots under the ColdFire port.
- `tools/verify/verify_euclid_fill.py` checks the Euclidean bit pattern
  against the same `(i·k) % n < k` law as `modules/euclid/control.c`.

## On the unit

Cursory testing on Sam's MKII (owner report, 16 Oct 2026).

## Gates

`tools/verify/verify_euclid_fill.py` (stage `image`) — fast, no port:

- Euclidean bit patterns (`(i·k) % n < k`, same as filter EUCLID)
- UI contract on `euclid_fill.s`: STEPS/PULSE/ROT labels, layout,
  PULSE default 5, STEPS locked via `ef_sync_len`, key layer, encoders
  A=PULSE / B=ROT / LEVEL=focused row
