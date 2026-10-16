# midi-follow implementation and verification

Each MIDI track can follow another MIDI track's chord root while keeping its
own rhythm, velocity and note length. By default, FIXED octave 3 with TRAN=0 uses MIDI notes 36–47:
C → F → G gives 36 → 41 → 43. The follower's TRAN adds a signed semitone
offset after its register choice. Scale Quantizer is not required.

## Composition and controls

Select `MIDI FOLLOW` with `MIDI PART STATE`; neither Harmony, Scales nor KITS
is required. RFOL is a persistent source choice, not a held modifier. Pressing
D opens its editor; TRIG/LIVE is a per-receiver setting. Start with TRIG so
roots change only at your programmed rhythm, then try LIVE for sustained bass.

## Register choice

On the receiving track, press **knob D (RFOL) on NOTE SETUP** to open FOLLOW.
Knob **B: MODE** selects FIXED or SOURCE. Knob **C: OCT** sets the register:

| MODE | OCT | Effect |
| --- | --- | --- |
| FIXED (default) | 0–10; default 3 | Keep the source pitch class in this octave, regardless of its original octave |
| SOURCE | -2, -1, 0, +1, +2; default 0 | Follow the source's complete root pitch, shifted by this many octaves |

For source notes C3 then C5 (MIDI 36 then 60): FIXED 3 produces C3 then C3;
SOURCE 0 produces C3 then C5; SOURCE -1 produces C2 then C4.
Octave names here use C0 = MIDI 0. Octave 10 is partial: only C–G fit MIDI.
Each mode remembers its own OCT value when switching modes.

The receiver applies register choice first, then its native TRAN/P-lock offset.
With Harmony active, root snapping and chord generation follow those steps.
Out-of-range final roots are silent, never wrapped or clamped. Settings affect
the next receiver note trig; already-held notes keep their original releases.
A chain uses the ultimate source's root and the final receiver's register and
TRAN; intermediate receiver offsets do not accumulate.

Source register refers to the harmonic root before inversion, spread and root
omission/placement, not whichever generated or arpeggiated note is lowest.
Source sequence TRAN/scale and live key root selection still happen before capture.

RFOL, MODE, both remembered octave choices and TRIG/LIVE response are native
Part settings per MIDI track. They are not parameter locked. UI edits use the
selected working Part; playback uses each track's playing Part. KITS carries
these native bytes but is not required. Existing stock controls and the source
selector remain in place. NO/YES/D or a track/page key closes the
window; transport and chromatic playing continue through it.

## On the Octatrack

1. Select the follower, for example **MIDI T2**.
2. Open **NOTE SETUP** with **FUNC + SRC** (or double-tap SRC).
3. Turn **knob D, RFOL**, from **OFF** to **T1**.
4. Program T1's C/F/G NOTE locks and optional NOTE2–4 chord tones. Its arp can
   play those chords. Program T2's rhythm; leave the follower's arp OFF.
5. Give the two tracks different output MIDI channels, then play.
6. On the follower's **ARP MAIN** page, use **TRAN** for relative pitch:
   **0** = root, **+7** = perfect fifth, **+12** = octave above, **-12** = octave
   below. Set it for the whole track, or hold a step and parameter-lock TRAN.
   A locked value replaces the track's base TRAN for that step; it is not added
   to the base. The follower's arp remains OFF.

RFOL appears on all eight MIDI tracks. It selects a **track**, independently of
its output CHAN. Several followers can select the same source. The selector
skips the track itself and choices that would create a circular dependency.
Chains resolve to their final source: T3 → T2 → T1 follows T1's root.

- **OFF** plays the track's original notes. Fresh Parts default to OFF.
- Root means the source's first NOTE, with its stock transpose/scale processing;
  it does not infer the root from a chord inversion. C–E–G arp notes leave the
  bass on C. A new F–A–C chord moves it to F.
- A configured follower is monophonic once its source has a known root:
  NOTE2–4 are suppressed. Before the first eligible source trigger it passes
  through unchanged.
- The next follower trig uses the selected source's latest root and the receiver's register choice. A held bass
  keeps its original note-off, including when RFOL changes or switches OFF.
- The follower's NOTE does not set an interval: use TRAN. Its live value,
  including parameter locks, is added after root selection without an additional
  scale correction. These are chromatic semitones, not scale degrees; +7 is
  always a perfect fifth, even when that pitch falls outside the source scale.
  Pitches outside MIDI 0–127 are suppressed instead of wrapped. Existing stock
  absent/invalid-note gates still apply before the follower replacement.
- A dependency chain uses the ultimate source root plus the final follower's
  own register choice and TRAN; intermediate followers' offsets do not accumulate.
- Ordinary same-tick source trigs are captured before any track emits, so
  **T2 following T8** sees the new root on that tick. Earlier microtimed bass
  trigs still use the previous root.
- Roots latch through rests and transport stops and remain runtime state.
  Configuration belongs to the native Part; roots and held-note ownership are
  not copied or persisted with it. This greenfield format has no migration
  from the previous volatile settings. Native Part operations own persistence.
- **Muting a source silences its sequenced MIDI output but keeps its root
  progression available to followers**, including when playback starts muted.
  Muting a follower independently silences that follower. Mute/unmute does not
  reset the remembered root or change the ownership of already sounding notes.
- Disabled tracks, CHAN OFF, zero velocity, invalid notes and rests still leave
  the previous root in place. Ordinary track mute is covered in linked and
  full-firmware emulator tests; unusual mute/plays-free modes remain untested
  on hardware.

On its own, MIDI Follow supplies bass-root following. MIDI Harmony optionally
adds live keyboard chords and follower chords/arp, as described below. Audio
following and live transposition of a running pattern are outside its scope.
Shared output channels have ownership stress coverage; physical MIDI timing
requires instrument validation.

## Stock firmware compatibility

A cold load in stock 1.40C preserves valid RFOL source numbers but resets the
shared flags and both octave bytes to zero in working memory. Stock does not
perform root following. Native SAVE PROJECT writes the normalized settings to
the current bank; it does not rewrite every other bank merely by loading.

After saving that bank on stock and returning to Follow:

- RFOL still selects the saved source.
- MODE is FIXED, UPDT is TRIG, and the fixed octave is **0**, not the fresh-Part
  default of 3.
- The remembered SOURCE offset is **-2 octaves** because its stored zero is
  biased by two. It takes effect if SOURCE mode is selected again.

This is measured by `verify_midi_saved_values_stock.py --scope follow`: all
256 input byte values across 16 banks, four working Parts and eight tracks,
with candidate → stock → candidate cold boots, native saves, and RAM/file
comparisons. It is not retained-memory firmware-switch or hardware proof.
Keep a separate project backup when returning to stock; this is not a lossless
round trip.

## Native address provenance

The stock Part validator is `0x40002318`; native Part initialization is
`0x40005638`, the bank writer is `0x400917c8`, and SAVE PROJECT is
`0x4008ee74`. These are existing firmware boundaries documented in Octabam's
BRAIN design and exercised by the Part and full-firmware gates.

| SETUP byte | Native count address | Candidate count | Stock count |
| --- | --- | --- | --- |
| 3: RFOL | `0x400d3efc` | 9 | 128 |
| 12: shared flags | `0x400d4082` | 16 | 1 |
| 13: fixed octave | `0x400d4086` | 11 | 1 |
| 15: biased relative octave | `0x400d408e` | 5 | 1 |

`bf_*_get` and `bf_*_play` in `settings.s` read these bytes through
`mp_read`; `bf_*_set` writes through `mp_write`. Part State owns selected
versus playing context, dirty flags and current-bank mirroring. The mapping
and clamp behavior are checked; the claim that these disabled stock slots
are suitable for extensions is a reverse-engineered design choice, not an
Elektron storage contract.

## Implementation

The module uses the linked ColdFire pattern from `modules/repitch` and the
stock NOTE descriptor, drawer and encoder dispatch. No DSP code is added.

- `0x4009f986`: before the output loop, capture eligible ordinary chord roots
  for all tracks. Uses the stock trigger mask, enabled-track checks,
  output channel and velocity. The mute mask is intentionally left to stock
  output handling. Original NOTE lanes already contain the locks.
- `0x4009fb00`: capture each eligible source event, including arp ticks, from
  the original NOTE lane, not the arp's scratch output. Apply the stock
  transpose and scale correction.
- `0x4009fb80`: resolve a follower's source, add its live TRAN (`a5+0x22c`,
  biased by 64), and replace its scratch pitch before
  stock note ownership and release bookkeeping (`0x4009fbbc` / `0x4009fd04`).
  Chained resolution has a defensive eight-hop bound.
- NOTE SETUP's unused D slot is labelled RFOL and enabled. Its encoder callback
  at `0x400bc64e` points to the module; its formatter prints OFF/T1–T8.
  The drawer detour at `0x40036674` reads RFOL from the selected native Part.

Native MIDI SETUP stores RFOL at offset 3, MODE/response flags at 12, fixed
octave at 13 and relative octave at 15. UI reads use the selected Part;
playback uses each MIDI track's playing Part through MIDI PART STATE.
`bf_roots[8]` holds the source's bass pitch or 0xff (unknown), and
`bf_pitches[8]` retains full MIDI root pitches. These histories are runtime-only.
Harmony calls `bf_register` before applying the receiver's TRAN; its adapter
also publishes live keyboard root octaves into `bf_pitches`.
Native Part operations own persistence, with or without KITS. The generic
MIDI sender is not hooked. The existing DRAM platform reserves about 10 MB of sample RAM;
this small module shares that reserve when composed with other DRAM modules.

## Root update timing: TRIG / LIVE

Press D on MIDI NOTE SETUP to open RFOL, then turn D inside the window
(**UPDT**, lower left). A/B/C remain RFOL, MODE and OCT.

- **TRIG** is the fresh-Part default and keeps the original behavior: the receiver
  uses the latest source root on its next scheduled note.
- **LIVE** also moves an already-sounding sequenced bass when the ultimate
  source changes root. It sends note-off for the old pitch and note-on for
  the new one, restarting the synth envelope. Rests stay silent. The original
  release deadline and the next programmed trig stay in place.

The setting belongs to each receiver in the native Part and takes effect
from its next ordinary trig (not an arp-only tick).
Live source-key changes are handled on the next sequencer service pass, not
held until the next receiver trig. This is not a measured zero-latency claim.
A source change coinciding with a scheduled receiver event does not add an
extra retrigger. Muted/disabled receivers and CHAN OFF do not generate notes.
Only voices owned by that receiver may move; occupied channel/note pairs
are not stolen. Out-of-range voices are omitted rather than wrapped.

With Harmony chords, LIVE shifts the currently sounding shape by the
logical-root interval; the next ordinary trig generates a fresh chord and
voicing. With an arp, its clock/order are retained and outgoing cached-pool
notes track the changed root. It does not trigger during an arp rest or
restart the arp. This control targets sequenced/arp receivers, including
those following a live Chord Play source; it does not retune manually held
receiver keyboard notes.

`tools/verify/verify_midi_follow_response.py` checks linked machine code,
release deadlines, silence gates and MIDI ownership. The companion
`tools/verify/verify_midi_follow_response_port.py --project /path/to/project`
operates encoder D through the emulated panel and captures the full firmware's MIDI output.
These tests do not establish physical MIDI latency or external-synth timing.


## Eight-track routing stress

`tools/verify/verify_midi_follow_stress.py` is an image gate. It tests all
40,320 permutations of a full eight-track chain, 12,000 seeded live routing
edits, and 56,080 routed outputs with register/transpose extremes, unknown
roots, cycles and invalid links. The independent graph model checks that
editing one receiver cannot change another, no selectable route introduces
a cycle, and runtime fallback terminates without writing outside its scratch
and stack. Run it on both standalone Follow and the combined Harmony image.
This exercises linked ColdFire code, not physical outgoing-MIDI timing.

## Verification

Run `make check REMIX=midi-follow` for the standalone module. The manifest
runs linked routing, register, response and graph stress checks. With a prepared
project copy, `verify_midi_follow_response_port.py --project DIR` checks LIVE
response through emulated panel events and MIDI output. `verify_midi_follow.py midi-follow --project DIR` covers routing, panel controls
and mutes; `verify_midi_follow_register_port.py --project DIR` covers register
selection. NOTE SETUP confirmation is covered by `verify_midi_part_settings.py`.
The separate Harmony integration has its own combination tests.
