# MIDI Scales

Extends the existing **KEY** control at the bottom right of MIDI ARP SETUP
(FUNC + AMP), without moving controls or replacing the graph.

## Controls

F selects OFF or any of the 12 keys in Major, Dorian, Phrygian, Lydian,
Mixolydian, natural Minor or Locrian. Encoder order groups modes by key.
The stock values 1–24 still mean exactly the original Major/Minor pairs;
25–84 append the other five modes. OFF remains zero. The existing Part
byte, working mirror, dirty flags, save/reload and Part copy store the choice.
It is therefore a **Part setting**, not a new per-pattern project field.

## Composition

Select `MIDI SCALES` in the remix. This module works independently. It extends stock sequencer/arp output
quantization; it does not generate chords. Existing Major/Minor playback
keeps stock quantization. Added modes use nearest scale notes, ties downward.
MIDI Harmony uses the same native choice for live keys and chord generation.
With MIDI Follow, the source's effective KEY is shown and F is read-only.

No audio tracks or Scale Quantizer settings are involved. Older firmware does
not understand values 25–84: set KEY to OFF or an original Major/Minor value
before using an edited Part on stock firmware.

## Verification

Run `make check REMIX=midi-scales`; the linked-code gate executes
all 84 combinations over all 128 MIDI notes and checks the formatter bounds.
Full MIDI/UI/project integration is shared with MIDI Harmony's reusable gate.
Hardware testing remains pending.

The extended KEY selector uses the stock movement accumulator at four raw
counts per choice, capped to one choice per report. This keeps nearby scale
choices selectable without changing their saved IDs. Physical feel is untested.

## First playing workflow

Set a track's output channel and program a few notes. Open MIDI ARP SETUP
with FUNC + AMP, then use F (KEY) to choose C Dorian. The sequencer's scale
correction uses C, D, Eb, F, G, A and Bb. KEY OFF removes scale correction.
Adding Harmony makes the same KEY control the degree roots and chord recipes.
