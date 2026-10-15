# MIDI upstream contribution plan

Scope: MIDI Scales, MIDI Loopback, MIDI Follow and MIDI Harmony, with the
minimum supporting changes needed for native behavior and reliable validation.
Excluded: MIDI Arp Presets/ARP templates, Sophie, Supersaw, new synth work,
POST FADER and unrelated effects. Stock upstream modules stay intact.

This is a preparation plan, not submitted PRs or a promise of upstream acceptance.
`codex/integrate/midi` is the complete verification branch, never the aggregate
PR. `main` follows upstream without local features. Each review branch starts
from current upstream main after its prerequisites merge. If a stack is needed
for review, label its base explicitly and retest after each rebase.

## Proposed sequence

| Order | Proposed PR title | Scope and prerequisites | Required evidence |
|---|---|---|---|
| 1a | Preserve edited page-two locks on trig release | Existing PLOCKS editor only; native edited/tap flags. No storage or capacity change. | Reproducer on unmodified upstream, held-step edit/release, copy/undo, project regression. |
| 1b | Initialize all KITS record-header fields | Two existing KITS header clears. Independent of new MIDI modules. | Empty/imported record initialization and native import/fallback regressions. |
| 1c | Deliver emulated MIDI input on scheduled frames | MIDI frame-input callback and its regression tests. Separate from firmware. | Scheduled versus delivered frames during long synthetic calls; RTOS tests. |
| 1d | Include transport's first MIDI event in captures | Capture boundary before transport starts; separate from scheduling. | Complete UART captures identical before/after, boundary counts corrected; symmetric Loopback controls. |
| 1e | Make boot-progress tests independent of host speed | Boot-progress helper/test only, if still required by current upstream. | Fast/slow host instruction budgets and unchanged runtime behavior. |
| 2 | Add MIDI Scales to native ARP KEY | Standalone seven-mode KEY extension, author source pin/adapter, gate, test remix and docs. No dependency on Follow/Harmony. | All 84 keyed choices over all 128 MIDI notes, stock choices, native Part behavior. |
| 3 | Add per-Part MIDI Loopback routing | MIDI Part State plus first consumer: EXT/INT/BOTH. Keep the shared foundation separate only if useful and independently testable. | Native Part copy/clear, settings, panel interaction, routing, complete note/CC captures, no leaked note ownership. |
| 4 | Route Scenes and USB MIDI through Loopback | Existing MIDI Scenes and USB integration; depends on Loopback. | External/internal/both destinations, Scenes producers, note-offs and disabled controls. |
| 5 | Add MIDI Follow | Part State; exercise Scales and Loopback only when selected. | Root/register/response behavior, mute/unmute, disabled mode equal to stock and combined ownership. |
| 6a | Support guarded companion saves in STORE | Optional checked callbacks and post-new-project notification. Original clients retain existing contracts. | Native failure does not copy companions; callback register-clobber tests, stock client regressions. |
| 6b | Provide protected per-track MIDI retained storage | MIDI SRAM, sparse-claim validation and necessary native MIDI copy/clear protection. If split, ledger optimization gets a separate PR. | Exact sparse-claim overlap equivalence, audio fields untouched, bounds, native copy/clear and restart. |
| 6c | Add MIDI Harmony with complete native lifecycle | Harmony engine/UI plus STORE/Part/retention support. Do not ship an incomplete save format or an obsolete intermediate storage design just to shorten a diff. | Degree/chord/voice math, panel/recording, save/load, corruption, all tracks, no-op observations and note ownership. |
| 6d | Compose Harmony with PLOCKS, KITS and Scenes | Explicit shared-hook adapter and selected combinations; depends on Harmony and required shared fixes. | Full 4,768 PLOCKS locks, 8,192 Harmony steps and 16,384 Scenes bytes; 18 KITS recall combinations; clear/copy/undo and rejected saves. |
| 7 | Document and qualify the combined MIDI bus remix | Selection, native MIDI octave/Quantizer compatibility, final manuals and cross-module fixture. | General check plus project-backed acceptance at the exact final commits. |

The standalone PIO first-sector write fix is required for dependable card-write
validation without STEM REC. Propose it separately with original author credit,
or use an equivalent fix already accepted upstream; do not bundle recording
features. The Quantizer/MIDI drawer fix is a separate compatibility candidate,
not a change to the independent KEY/Scale Quantizer semantics.

Harmony is the largest review item. Before submission, inspect whether its engine,
UI and degree extensions can form independently usable increments. If they
cannot, keep one coherent feature PR with a reviewed commit series and a source
map; do not fabricate a working intermediate version. Review author-source
changes before pinning them: a three-line adapter must not conceal an unreviewed
large source addition. Include direct source-commit links and per-stage diffs.

## Author repository and adapters

The migration keeps the tested native paths and uses the existing guarded staging
workflow. External author adapters are not yet claimed complete. Convert each
module alongside its small contribution: derive source paths from the author's
manifest location, ensure generators and gates resolve the same source, and
verify standalone and combined builds. Do not add another registry or builder.
The author repo supplies source; Octabam owns its schema, STORE, KITS, PLOCKS,
emulator, tools and integration. Shared fixes belong in Octabam PRs.

## Review contract

- Rebase onto current upstream main, then run current CONTRIBUTING.md's required
  `make reach RUN=1 KEEP=1` checks, plus feature/combination regressions.
- Every step builds independently and keeps its declared tests passing. A result
  on the full integration branch does not qualify a smaller PR automatically.
- Keep branch-specific docs and generated indexes accurate; include only files
  relevant to the behavior described by the PR title.
- Report source, emulator, package and physical-device evidence separately.
- Prepare PR descriptions with problem, resulting behavior, dependencies, author
  source pin, exact checks/results and remaining limits. Submit only after the
  user reviews the series; never merge upstream automatically.

## PR description pattern

Problem: describe the concrete trigger and its previous behavior.
Change: explain the resulting behavior and the small boundary this PR owns.
Dependencies: upstream base and any prerequisite PR; exact author-source commit.
Validation: commands and results on this rebased snapshot, including meaningful
negative controls and selected combinations. State skips explicitly.
Limits: hardware status, untested boundaries and why remaining work is separate.

## Verified extraction dependency: TEMPO SYNC symbols

The MIDI-only extraction initially differed from the completed image by three
bytes: the TEMPO SYNC hook target. Generic `cave`/`replay` symbols collided in
the combined selection. Preserve the completed branch's unique
`tempo_note_publish`/`tempo_note_replay` names and installed-hook gate as a
small compatibility PR before the final bus selection. This introduces no new
effect behavior; the wrong hook is measurable without a hardware claim.

## Prepared branch status

The first independently extracted candidates are `codex/pr/plocks-editor`,
`codex/pr/tempo-hook-symbols`, `codex/pr/kits-header` and
`codex/pr/midi-scales`. Each starts at the recorded upstream base; none depends
on the aggregate integration branch. Their exact commits, tests and limits are
in the author repository’s `integration/review-branches.json`. KITS is held for broader recall
qualification despite passing its dirty-header regression.

MIDI Scales has a deliberately small, independent author-source review branch
with the same name. Its pinned adapter demonstrates upstream's preferred
submodule pattern without including Harmony or the other modules in that
author history. The remaining feature stages above are planned boundaries,
not yet submission-ready branches. Prepare them sequentially after predecessor
review; validate their adapters and exact combinations before opening PRs.
