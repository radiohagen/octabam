# Harmony MIDI bus

The complete MIDI integration is on `codex/integrate/midi` in
[radiohagen/octabam](https://github.com/radiohagen/octabam), extracted onto
upstream `2d1cbcf471cf8b63e2279b3c372a6ebb47456a99`. The original completed
source is `03f7e81aee53d1d0b0c16ef1694bb10a35dcb63d` from the preserved local
`codex/experiment/harmony-track-sram` branch. Its mixed private history is
not part of this public integration. Original OCTABAM85 tags remain unchanged.
This acceptance branch is not a proposed aggregate upstream PR.

Selects upstream octabam-bus plus MIDI Scales, Follow, Harmony and Loopback,
with their Part/STORE, copy-protection and compatibility support. Excludes
MIDI Arp Presets, FM Synth/Synth Machine, Sophie, Supersaw and POST FADER.

## Storage and integration boundaries

Harmony uses track-local retention: each step's degree/chord token occupies
that same MIDI step's two reclaimed bytes. Metadata remains inside the same
track. No track borrows another track's capacity, and Harmony reserves no
contiguous tail SRAM. Native track clear removes its Harmony locks; copy,
paste and undo carry the appropriate musical data. See the
[layout and lifecycle contract](../../modules/midi-harmony/DEVELOPMENT.md).

PLOCKS P2 keeps upstream's storage at `0x100f8600..0x100fbdf0`, its `P2NV`
format and its 4,768-lock unsaved recovery capacity. There is no PLOCKS
compression or relocation. Its only runtime source difference from upstream
is the separately committed trig-release editor fix (`12d34f68`): native
edited/tap flags prevent releasing an edited trig from deleting its new lock.

MIDI Scenes retains all 16,384 bytes and its runtime matches upstream.
KITS retains its upstream reservation and the earlier two-line record-header
initialization correction from OCTABAM85 (`44a7c6b9`). Shared copy/STORE
integration, the PIO write fix and Quantizer MIDI drawer adapter remain selected.
These are not removed by moving Harmony's retained data.

Harmony writes HDP4/HMT2 with per-step ACC. P2LK is unchanged. There are no
alternate Harmony retention layouts or migration readers. The MIDI bytes are reverse-engineered reclamation, not an official
free-space contract. MIDI SRAM protects them against native bulk writes and
strips them from native DRAM, clipboards and bank files; Harmony's lifecycle
hooks perform the musical copy/clear operation and checkpoint the result.

## Accumulator candidate

The Harmony accumulator update is imported from preserved source
`510e0aee`. It does not change the integration base pinned in
`integration/octabam.json`, and the historical BUILD 79 results below do not
qualify this new candidate. Its focused source-build evidence uses BUILD 80,
PGO off, MAIN OS SHA-256
`576403a42614a5b0a18c098a748ed9b9488ffed44f060f072a4dc9103fbd203b`.
See [Harmony development](../../modules/midi-harmony/DEVELOPMENT.md) for
the gates and hardware boundary. Retained storage capacity is unchanged;
ACC adds 75,776 bytes of working configuration in DRAM plus transient phase.

## Historical completed-source validation

The final firmware is BUILD 79, `OCTABAM_PGO=0`, SHA-256:

```
98e809740dcb5411c6498cc1e1a7a48e052f1c44652b5c269b7ed13f154e6856
```

`make check REMIX=harmony-track-bus BUILD=79 OCTABAM_PGO=0` passed. Its image
stage ran 47 gates with zero failures, including one redundant direct
track-retention run. Final registration uses the existing packed-storage
entry point, which already dispatches to the track regression.

All 24 dedicated suites passed. They cover the general run's 13
project-dependent skips; those skips are preserved and mapped to their
successful project tests in the [published source receipt](https://github.com/radiohagen/octabam/blob/codex/integrate/midi/docs/guide/MIDI_SOURCE_VALIDATION.json).
The [migration receipt](https://github.com/radiohagen/octatrack-modules/blob/main/integration/migration-validation.json)
separately records checks rerun in the radiohagen workspaces.

| Coverage | Result |
|---|---|
| Harmony lifecycle | All nine groups: sequencing, recording/save/load, panel editing, copy/clear/undo, Parts, projects, corrupt files, playback and representation boundaries |
| Track retention | All 765 legal tokens, 134 corruption cases, first/middle/last track clear, interrupted saves and 20 intervening UI polls |
| Combined retained capacity | 8,192 Harmony steps, 4,768 PLOCKS locks and all 16,384 MIDI Scenes bytes through checkpoint/restart, track clear/restart and New Project/restart |
| KITS and Scenes | All 18 OFF/NOTE/CHORD recall combinations with Scenes and SIZE 4; native KITS persistence/import/fallback; Harmony and upstream Scenes persistence |
| MIDI behavior | Scales, Follow including mute/unmute and stock-OFF controls, dense eight-track playback, Loopback panel/producers/routing/controls and note-release ownership |
| Upstream bus features | PLOCKS editing/save/recovery, project playback, tempo controls, FX2 protection, defaults/templates, load-meter calibration, USB isolation and reserved-memory writes |

Implementation validation also found and fixed a Harmony NOTE-to-OFF KITS
recall stall (`387d998b`): unchanged observations of a detached outgoing Part
must not repeatedly invalidate its checkpoint. The focused negative control
failed before the correction; the native-copy regression and all 18 full
recall combinations pass afterward.

Two Loopback test failures were instrument/setup issues, with unchanged
firmware. The emulator sampled its MIDI counter after transport could already
emit the first step; moving the counter before start preserved all eight
complete UART captures byte-for-byte. Equalizing the control test's destination
setup calls removed a finite-capture LFO endpoint mismatch. Exact MIDI and
receiver-write assertions remain in place. Initial failures, controls and
successful reruns remain in the receipt; see the
[transport capture trap](https://github.com/radiohagen/octabam/blob/codex/integrate/midi/docs/contributing/TRAPS.md#trap-transport-capture).

Earlier `67af4803...` results and the plain-upstream PLOCKS failure control
remain under `out/track-evidence`, `out/track-control` and
`out/track-plocks-control`. They are historical evidence, superseded by the
final image above. The final general run did not reproduce the earlier USB
packet-size failure.

## Reproducing project checks

Use disposable project copies. With the project virtual environment:

```
BUILD=79 REMIX=harmony-track-bus OCTABAM_PGO=0 .venv/bin/python tools/verify/verify_harmony_track_port.py --project <source>
.venv/bin/python tools/verify/prepare_kits_acceptance_fixture.py --project <source> --out <new-dir>
```

The fixture helper creates `native/project`, `rejected-bank` and
`octakit-v3-synthetic`. Pass those to `verify_kits.py` as `--project`,
`--strand-project` and `--octakit-project`. Its synthetic import generations
exercise fallback from a damaged newer record; they are not an author's backup.
The helper records hashes and verifies the source is unchanged. Exact commands,
image identities, worker/emulator identities and per-suite logs are retained
under `out/track-completion-evidence`.

Physical battery-backed power-off recovery, device timing and hardware MIDI/audio
remain untested. This is an experimental, software-validated build, not a new
release or card installation. No stock firmware or generated firmware belongs
in Git.
