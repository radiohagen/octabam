# Degree roots and persistence

Internal implementation of [MIDI Harmony](../README.md). C files are the
authoritative source; regenerate assembly with `python3 modules/midi-harmony/degrees/generate.py`
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
No earlier experimental format is migrated. Harmony uses its own companion
identity and rejects incompatible experimental CHRD formats.

KITS uses the same native Part fields and requires no special adapter.
The optional MIDI SCENES adapter uses upstream's full-table scene API.
Its [compatibility boundaries and validation](SCENES.md) are documented
separately. See [native Part storage and KITS boundaries](KITS.md).

## Compact HDP3 / HDN3 storage

The experimental `RETENTION=MIDI TRACK` layout uses fields 30/31 of each
MIDI step in the current-bank CS1 mirror. Each step's ten-bit DEG/CHRD token
is stored at that **same pattern, track and step**. No track borrows another
track's capacity. All 8,192 steps can carry both locks. Part defaults remain
native Part data and runtime ownership/voicing history remain transient.

Each 128-byte lane uses the upper six bits of steps 1..22 for its own
16-byte header: version, bank, lane, representation/scale, status, three
reserved zero bytes, generation, and checksum. Remaining upper bits are zero.
Step 0's upper six bits are the commit marker. The lane checksum covers its
header identity and canonical 81-byte HDP3 payload. All lanes must have the
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

The old `LEGACY` and `SHARED` layouts remain available for focused historical
checks; neither is selected by the experimental remix. Do not combine SHARED
with unmodified upstream PLOCKS. There is no automatic migration from either
old SRAM layout: save the project with the previous firmware first. Existing
HDP3 companion files and working tables are unchanged.

Each of 128 lanes stores one byte (`state*84 + outgoingScale`) and 64 ten-bit
values (`degreeIndex*9 + qualityIndex`, MSB first). Degree index 84 and quality
index 8 mean unlocked. Thus the payload is 128 × 81 = 10,368 bytes, plus its
32-byte bank/version/checksum header. Every step can have both locks; there
is no sparse limit, lossy truncation, variable worst case or overflow journal.
HDP3 files and HDN3 retention use version 3. HDP0 remains the empty marker.

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

No earlier Harmony format is migrated. Use a disposable project copy for
first testing; remove its old `hdeg*.work` / `hdeg*.strd` companions to start
fresh. Existing incompatible companions are rejected and protected from
being overwritten by a save. Preserve the originals with the older firmware.

`verify_harmony_degree_packed.py` checks independent bitstream oracles, dense
banks, malformed payload rejection before publication, post-checkpoint native
edits and edit reversions, reservation guards and a preempting saver. The
musical, publication and full-firmware suites validate the surrounding paths.
