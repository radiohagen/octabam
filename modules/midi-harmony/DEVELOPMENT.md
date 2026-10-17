# MIDI Harmony implementation

Internal implementation of [MIDI Harmony](README.md). C files are the
authoritative source; regenerate assembly with `python3 modules/midi-harmony/generate.py`
and verify drift with `--check`.

## Musical contract

OFF uses native NOTE and NOT2–4. HARM NOTE and CHORD use one degree/register
value, displayed as `1:3` (degree 1, tonic octave 3). Degree 7 advances to
degree 1 of the next tonic octave. Thus `7:3` is B-flat3 in C minor but C4 in
D minor. Octave names follow the native display (MIDI 60 = C4).

When a fresh or missing Harmony value requires a fallback, use `1:3`,
resolving to C3 under C major. Existing native notes are converted on entry;
the fallback does not replace them.

- OFF -> HARM converts absolute NOTE into degree/register using the applicable
  KEY. Nearest in-scale pitch wins; exact ties choose the lower pitch.
- NOTE <-> CHORD keeps the degree unchanged.
- KEY changes while HARM is active preserve degrees and change resolved pitches.
- HARM -> OFF writes resolved roots into native NOTE before native playback
  resumes. It preserves NOT2–4. It does not restore old absolute roots.
- A later OFF -> HARM uses the KEY at that later transition, establishing new
  degrees. KEY changes while OFF receive only stock processing.
- KEY OFF uses C major for degree conversion/resolution. Existing no-scale
  chord recipes remain unchanged (TRI makes major intervals on the root).
- TRAN/arranger offsets operate on resolved pitches, once. They are not baked
  into stored roots during conversion. Voicing, spread and ROOT are likewise
  output treatments, never inputs to representation conversion.
- Scale-derived CHRD choices adapt to the current scale. Explicit MAJ/MIN/DOM7
  preserve their interval recipes.
- A degree outside the MIDI range is silent in HARM. On conversion to OFF,
  which has no separate silent-root representation, it commits to the nearest
  MIDI boundary (0 or 127). It never wraps octaves or removes a root lock.

## Data and lifecycle contract

Native NOTE always remains a valid pitch or its native unlocked sentinel.
Harmony degree defaults and locks are separate data. Only the selected
representation is authoritative; conversion synchronizes at OFF/HARM boundaries.
Degree locks preserve native lock presence and Part-default inheritance.
Edits publish each root and its native snapshot together under a short
interrupt mask. Recording uses the same boundary; bank retention runs after
interrupts are restored. Clearing a HARM root removes its native mirror with
the degree so an intervening reader cannot reconstruct the deleted value.

HARM, Follow, voicing, DEG and CHRD defaults belong to each native Part.
Explicit DEG/CHRD locks stay with their patterns. An explicit HARM edit converts
the edited Part's default and its attached pattern roots. Recall inherits the
incoming Part's defaults. HARM-to-OFF locks preserve the outgoing scale's root;
for example, C-minor 1:3 becomes native C3 even when the incoming OFF Part has
D-minor KEY. A transient outgoing snapshot protects replacement of the same
physical slot. Inactive patterns retain their last scale until next used.

Native Part Save/Reload/copy/clear carries defaults directly. The companion
contains only 128 pattern/track root records: 64 degrees, 64 native edit
snapshots, representation, outgoing scale and context in runtime memory. Reusable slot context
is detached on load and before replacement. Part assignment and defaults are
excluded from the native pattern fingerprint. Dirty flags and retained mirrors
follow native bank ownership.

Native pitch consumers and generated note ownership receive real pitches.
Recording captures degree identity at the event, not a later queue-consumption
KEY. Releases retain their original track and emitted pitches. Pending events
cannot mix old representation data with a new mode. UI reads do not regenerate
AUTO voicing. The UI queue boundary reconciles the selected pattern even when
stopped; no trig is required for an OFF/HARM mode boundary.

Copy, paste, undo, clear, new trigs, new projects, bank load/store/reload,
Part save/reload/copy, Save As and battery retention carry the degree data
alongside their native counterparts. Corrupt or mismatched storage cannot
publish partially validated data. A rejected working save cannot overwrite
the stored bank/companion backup. Native bank and companion writes remain
separate filesystem operations; arbitrary power-loss atomicity is not claimed.
Harmony uses its own companion identity and rejects incompatible experimental
CHRD formats. Obsolete companions are rejected and protected from overwrite.

KITS uses the same native Part fields and requires no special adapter.
The optional MIDI SCENES adapter uses upstream's full-table scene API.
Its [compatibility boundaries and validation](SCENES.md) are documented
separately. See [native Part storage and KITS boundaries](KITS.md).

## Compact Harmony storage

The sole track-local retention layout uses fields 30/31 of each
MIDI step in the current-bank CS1 mirror. Each step's ten-bit DEG/CHRD token
is stored at that **same pattern, track and step**. No track borrows another
track's capacity. All 8,192 steps can carry both locks. Part defaults remain
native Part data and runtime ownership/voicing history remain transient.
ACC adds a four-bit amount in the same step word. Zero means inherit, one
means OFF, 2…8 encode −7…−1, and 9…15 encode +1…+7. There is no freeze code.

HMT2 uses each word's low ten bits for DEG/CHRD, next four for ACC, and top
two for metadata. Step 0's top two bits are the aligned commit marker.
Steps 1…63 carry an 11-byte header (version, representation/scale, status,
generation and checksum), four setting bytes, four default-amount bits, and
two zero reserved bits. Expected bank/lane identity is included in the hash
without spending stored bytes. The checksum covers that identity, header
fields and the canonical 81-byte root lane plus 37-byte ACC lane. All lanes must have the
same bank generation/status and pass validation before any runtime data is
published. Lane 0's marker is cleared before changes and published last in
one aligned word write. Bulk encoding and writes run with interrupts enabled;
the existing outer-writer/generation protocol retries a preempting update.
An incomplete bank checkpoint falls back to the validated companion files.

Storage remains SRAM-only: MIDI SRAM protects the fields during native bulk
operations and strips them when copying into native DRAM, clipboards and bank
files. Harmony's existing edit/copy/undo hooks carry the musical data, then
checkpoint it to the matching destination steps. A track clear removes that
track's Harmony locks; preserving storage against native bulk writes does not
preserve deleted musical content. Native byte-for-byte copies alone are not
a valid Harmony transfer because context, lane identity and checksums differ.

This layout claims no contiguous tail SRAM. PLOCKS P2, MIDI Scenes and KITS
retain their upstream reservations. PLOCKS P2 retains upstream storage
and its 4,768-lock recovery limit. Its separate trig-release editor fix does
not alter storage.
HARMONY PLOCKS still composes their shared editing/copy hooks. The protected
fields are reverse-engineered reclamation, not an official free-space contract.

There is one implementation: degree-based NOTE/CHORD, ACC, HDP4 companions
and HMT2 own-step retention. Native OFF behavior and representation conversion
remain. There are no legacy retention options, alternate popups or migration
readers. All builds require MIDI SRAM, MIDI Part State and STORE.

HDP4 contains a 10,368-byte packed root/quality section, then appends
128 ACC lanes of 37 bytes: 32 packed amount bytes followed by signed LOW,
HIGH, BOUND, RESET and default amount. Its version-4 header is still 32 bytes,
making a 15,136-byte companion. Validation checks the complete payload before
publishing either roots, qualities or ACC. The default cannot be INHERIT.
All SRAM metadata/configuration still fits in the existing 16,384-byte pool;
PLOCKS and MIDI Scenes lose no capacity. Working configuration adds 75,776
DRAM bytes across 16 banks; phase/direction uses 128 bytes per active MIDI
track, plus event identity bookkeeping. The phase is never written to SRAM.

Stock 1.40C does not interpret these companions. MIDI SRAM strips all reclaimed
bytes from native bank files, so ACC adds no new native field values. An older
Harmony build cannot read HDP4/HMT2; save a disposable backup before switching.
Stock edits that change Harmony's native NOTE/trig fingerprint can cause a
later Harmony load to reject the companion. Physical stock round-trip and
power-off results must be reported separately from emulator/file checks.

Each of 128 lanes stores one byte (`state*84 + outgoingScale`) and 64 ten-bit
values (`degreeIndex*9 + qualityIndex`, MSB first). Degree index 84 and quality
index 8 mean unlocked. Thus the payload is 128 × 81 = 10,368 bytes, plus its
32-byte bank/version/checksum header. Every step can have both locks; there
is no sparse limit, lossy truncation, variable worst case or overflow journal.
HDP0 remains the empty marker in all builds.

**Snapshot reconstruction is an invariant, not a guess.** Every HARM root
publication writes native NOTE and its runtime edit snapshot as the degree's
C-major reference pitch, clamped to MIDI bounds (unlocked remains 255).
Playback always resolves DEG through the applicable KEY. HARM-to-OFF writes
the outgoing KEY's real pitch before native playback resumes. OFF NOTE and
NOT2–4 remain native. Recording still captures the physical input's degree
at the original KEY, and never records generated chord tones.

This stable native mirror is independent of later KEY changes. Storage can
reconstruct its exact snapshot from DEG; a later native NOTE edit, including
an edit reverted to the old value, remains detectable. Arbitrary historical
snapshots and a one-bit match flag are unnecessary. Non-HARM snapshots are
unused by the conversion policy and load as unlocked. Slot context is
transient and detaches on load, as before. Packing rejects a HARM record
whose snapshot violates the invariant instead of discarding information.

Native/degree publication stays under the existing short interrupt masks.
Before a Harmony native write the old retained checkpoint is invalidated,
so an interrupted publication cannot reinterpret a new reference pitch as
an absolute edit against an old degree. Explicit save paths and the UI-task
poll commit the refreshed snapshot with magic last. A preempting saver only
requests a retry: one outer writer owns the retained bytes. Bulk copying is
interruptible. UI polls do not request another save while that writer is busy:
repeated polls otherwise advance its generation indefinitely when a checkpoint
spans a UI tick. Real edits still invalidate the checkpoint and force a retry.
Likewise, repeated reads of a detached outgoing Part during KITS recall must
not increment revisions when the roots, scale and context have not changed.
Otherwise a higher-priority checkpoint writer can starve the interrupted Part
copy. The Part-state gate checks repeated observations during a paused native
copy, and the full KITS gate checks held notes across NOTE-to-OFF recall.
As with previous retention, power loss during an invalidated
or incomplete checkpoint falls back to validated companions; this does not
claim atomic unsaved-edit recovery at every power-loss instruction.

Earlier Harmony formats are not migrated.
Use a disposable project copy for first testing. Incompatible companions are
rejected and protected from being overwritten by a save; preserve the originals
with the older firmware.

## Accumulator hook and UI provenance

Transport reset observes both native start stores: cold start at `0x4009c3d4`
and resume at `0x4009c4d4`, replaying `move.l d0,0x800065b8` after preserving
the caller's registers. These stores are documented in
`docs/firmware/STEM_REC.md` section 1.3. The earlier cold-start staging-copy
hook alone missed STOP/PLAY resume. Both edges now request a reset; the next
actual note event resolves its incoming pattern's reset policy. The port gate
checks a real STOP/PLAY journey, while linked checks cover both continuations,
register/stack preservation and the NONE policy.

The successful-note continuations at `0x4009fbb2` and `0x4009fcfa` follow the
stock sender calls at `0x4009fbac` and `0x4009fcf4`. Disassembly of stock 1.40C
(MAIN OS base `0x40000400`) shows ownership-rejected paths bypass these calls.
The six claimed bytes replay the original sign-extended status-byte load into
D1/D0 respectively; no interior branch target was found in the native path.
The accumulator additionally excludes zero velocity and live arp pools.
The linked gate exercises both continuations; the full-firmware gate observes
sequenced notes, chord tones and arp repeats. Physical DIN timing remains untested.

The window reuses native modal creation/input layers and encoder widgets.
Its right-hand separators call stock's alternating-pixel line routine
`0x40012004(surface,x0,y0,x1,y1,phase)`, also used by native SETUP drawing;
selector and footer boundaries use `0x40012254`. No UI work runs in the
sequencer or interrupt hooks. The port gate supplies physical button/encoder
events and captures both sections for visual inspection.

The pixel gate measures composed 1-bpp LCD ink, including the longest captured
labels, against the native frame and dotted cell boundaries. Horizontal padding
differs by at most one pixel (at most half a pixel of centre error); vertical
padding is 1/1 pixels for CHORD groups and 4/4 for ACCUM groups. Each of A–F is
also exercised independently through panel events in both sections: A/B/C map
to the top row, D to the bottom-left cell, and empty E/F cells ignore turns.
The checks compare the complete Harmony Part settings and ACC configuration,
not just the intended field. Held-trig settings remain track-wide and held E
press on NOTE MAIN restores inheritance. This is emulator LCD/input evidence,
not physical encoder or display acceptance.

The Part initialization harness retains the common degree-aware instruction
allowance instead of overriding it with a smaller one-million-instruction cap.
With ACC, linked `ch_lock_init` completes after 1,023,352 emulated instructions;
the old cap stopped inside `hd_roots_reset_c`, before the return assertion.
The unchanged Part/default/inheritance assertions pass with the existing
degree-aware budget. This count is harness evidence, not hardware timing.

`verify_harmony_degree_packed.py` checks independent bitstream oracles, dense
banks, malformed payload rejection before publication, post-checkpoint native
edits and edit reversions, reservation guards and a preempting saver. The
musical, publication and full-firmware suites validate the surrounding paths.

## Source organization

All implementation files live directly in this module. `generate.py` compiles
all C units, including SIZE, and checks them as one set. Musical units remain
separate files; flattening does not merge everything into one source file.
Original paths and retired files remain recorded in `integration/sources.json`.
The staging tool removes only recorded, tracked old paths at the pinned baseline.

## Accumulator validation

Harmony is greenfield and has no released-user migration obligation. Existing
historical format readers have been removed, not maintained as a compatibility promise.
Acceptance focuses on current settings, native project preservation and reliable
save/reload/retained recovery.

The import comes from preserved source commit `510e0aee`; per-file hashes
are recorded in `integration/sources.json`. The focused linked gate covers
boundary policies, reset policies, actual-sound advancement, dense packing,
obsolete-format rejection and native transport-hook ABI preservation. Its skip-advance
negative control must fail.

The full-firmware accumulator gate exercises real panel events, each A–F
control independently in both sections, held trigs, transport restart,
chord/arp output, Follow plus TRAN, retained restart and native project
save/cold reload. The pixel gate measures actual composed LCD ink against
cell boundaries. Dense coexistence covers all 8,192 Harmony/ACC steps,
4,768 PLOCKS locks and 16,384 Scenes bytes.

Run these in a staged Octabam worktree, not this source-only repository:

```sh
.venv/bin/python tools/verify/verify_harmony_accumulator.py harmony-track-bus
.venv/bin/python tools/verify/verify_harmony_accumulator_port.py --project /path/to/copy
.venv/bin/python tools/verify/verify_harmony_accumulator_ui.py out/harmony-accumulator-port/panel-note
```

These are software and emulator checks. They do not establish physical display,
encoder, DIN timing or battery-backed power-off acceptance. See
[implementation and measured layout](DEVELOPMENT.md).

### Pre-consolidation author-repository staging, 2026-10-17

The pre-consolidation author source at `030e886` builds on the unchanged integration pin
`8f8e00d061d17a890a3b01d5f340492f912712e2`, BUILD 80, PGO off.
Its MAIN OS is 1,228,366 bytes, SHA-256
`f5e043e953fc2f486b732e34c9c34bb45077143ede25be499bd7d7de092d2fd7`.
It is not byte-identical to the earlier preserved-source image: 100 of 101
runtime objects are identical; only BRAIN differs, because the author repo's
existing module credits use `radiohagen`. Its generated credit strings account
for the changed layout/relocations and compressed image.

Source checks, all 15 author-repository tests, generated assembly, the staged
linked accumulator gate and native Part initializer gate pass. Suppressing
actual-sound advancement fails the negative control at the expected 48-versus-50
assertion. An empty project directory initially invalidated the port test setup;
the accumulator port gate now rejects it before building a fixture. Keep those
failed runs separate from valid-project results.

The fresh full-firmware accumulator run passes all 12 result groups on that
staged image: panel defaults/locks, sequence, unsaved retained restart, native
transport reset, setup navigation, measured pixels, each positional encoder,
standard/held controls, native project save/cold reload, chord, arp and Follow
plus TRAN. Follow's unchanged UI also passes its 32-render gate and full-port
register/lifecycle suite. These results do not replace broader regression or
physical-device acceptance.

The preserved-source general check completed 47 image gates with one failure:
the old Part initializer instruction cap. The corrected focused gate passes without weakening its
behavioral assertions; that initial general run is not a clean all-pass result.
