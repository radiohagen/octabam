# Bus DSP optimization and post-fader routing review

This record explains the changes to Sam Banks's (`sambanks`) BusDelay and
BusVerb, the evidence for preserving their behavior, and the separate adaptation
of [PR 542](https://github.com/sambanks/octabam/pull/542). It is an engineering
review of a candidate change, not a hardware acceptance record.

The original algorithms and their attribution remain in place. The DSP work
removes repeated or inaudible computation; it does not replace the algorithms,
reduce their precision, shorten their buffers, or reduce the configured grain
count. The POST FADER adaptation credits `sanderlegit`. Its normalization rule
intentionally differs from the PR to satisfy the requirement that muting one
source must not change another source's send gain.

## 1. Scope and reference

| Layer | Reference / change | Required behavior |
|---|---|---|
| Original DSP | Upstream `f8141428248a5265eb5dee9645b0adef9ab08baf` | Behavioral oracle for the optimizations |
| Pure DSP optimization | `3a0b2d22` | Identical 24-bit audio for equivalent inputs, controls and state history |
| Optional POST FADER / RETURNS | `f7f8e174` | LEVEL/mute/solo-aware excitation, stable other-source gain, independently audible tails |
| Integration fixes and reliable image extraction | `7fd8d151` | Preserve dispatcher flags and held notes; test the supplied image's actual code |
| Startup and audit follow-up | This review | Seed the first active send from current controls; add sounding-host, adversarial-state and provenance checks |

The PR snapshot reviewed was head `2b4b0ed1` (unmerged when fetched). The
maintained local prototype was `codex/modules/post-fader` at `0f45b499`, with
implementation commit `9b9e2060`. Its historical results do not qualify this
new image. Sam Banks's return protocol was adapted to the current memory map.

The first measurements were built at upstream `d1f32c7c`. The two engine
sources are unchanged between that revision and `f8141428`. The original
measured branch was based on `f8141428`; neither a moving remote branch nor an earlier
PR build is the behavioral oracle.

For the initial publication to the `radiohagen/octabam` fork, upstream
`92a63bacc51ebf4c5c80a930670a9c7e973e150e` was merged on 27 October 2026.
Its two additional commits change only `FAILURE_MODES.md` and `DEMAND_LOAD.md`;
firmware sources, build inputs and verification tools were unchanged in that
synchronization. The original published history is retained in
`codex/backup/bus-dsp-before-rebase-20261029` at `d45d80c4`, including the
measured commits and reproducible source references below.
Documentation checks passed again after this synchronization; audio measurements
were retained because their executable inputs did not change.

The optional combination is selected by
[`test/send-return-poc`](../../remixes/test/send-return-poc/README.md).
The default `octabam-bus` selection does not acquire POST FADER or RETURNS.
Pure DSP comparisons use `test/bus`, the shipping two-core/32K delay geometry,
with matching grain counts on both sides. They do not compare four grains to
two grains and call the quality change an optimization.

## 2. What changed and what must remain invariant

### BusDelay

The original left and right GRAIN loops calculate the same control quantities
for corresponding grains: read distance, window gain and fractional position.
The left loop now calculates these once and saves them in the former right
control-record scratch slots (`r7+$4c..$57`). The right loop reuses them.
Each channel still reads and interpolates its own audio. The multiply,
rounding and accumulation order that produces each channel's signal is retained.
The two-grain source substitution is tested separately.

The sharing invariant is checked in source and execution: warm-up clears both
original control banks, their recurrences use identical phase/scatter/window
inputs, and neither recurrence depends on channel audio. Mode exits leave both
banks unchanged. Cached values have already passed their original limiting
steps; the fractional position remains exactly representable.

Small move/pointer changes remove redundant work in CLEAN and REVERSE as well.
Saturating accumulator moves must not be replaced by unrestricted transfers;
the retained moves and the fixed-point interpreter are part of the equivalence
argument. The buffer geometry, pitch/scatter/density behavior, feedback,
parameter smoothing, mode defaults and output latency are not intended to change.

The existing 8,192-NOP delay read-back pad remains. This does **not** prove DMA
safety: finishing computation earlier moves the following copy earlier even
when the pad is unchanged. The emulators do not establish the available timing
margin. See [the trap register](TRAPS.md#trap-rep-dma) and
[hardware failures](FAILURE_MODES.md).

### BusVerb

The shimmer interpolation/windowing/output calculation is skipped only when
the **glided** shimmer gain is exactly zero. Checking the panel target alone
would cut the fade-out and is not sufficient.

The write buffer, filters and both phases continue advancing while shimmer is
inaudible. Enabling it again must resume the same state as the original code.
The skipped tank-input write adds an exact zero. Scratch words `$14/$38`
need not retain the old inaudible values, but are freshly written before active
use. The active shimmer path has an additional three-instruction guard. The tank,
limiter, tone, modes, diffusion, gate and feedback design are unchanged.

### POST FADER and RETURNS: deliberate behavior changes

POST FADER scales the transient DSP send controls by `(LEVEL/128)^2` using
the MAIN mixer snapshot after mute/solo. It does not rewrite the Part, saved
project, displayed knobs or MIDI feedback. It is a LEVEL-aware control path,
not an exact post-mixer audio tap: scene XLV, cue gain and stock's per-sample
mixer ramp are outside this implementation. AMP VOL already affects the audio
reaching the effects.

A tag carries the original nonzero send's participation independently of its
scaled gain. DSP consumers use the tag for the existing `1/sqrt(N)` client
count and remove it before amplitude arithmetic. Thus a muted or faded source
stops adding audio through the existing smoothing without changing the other
sources' normalization. Turning the original send knob through zero still
changes membership. This is intentional and differs from the PR's suggestion
that muted sources stop counting.

Fractional precision is retained except in BusDelay REV: its low byte belongs
to the held MIDI note, so the coefficient retains its original seven-bit
precision. A note alone must not register a reverb sender. IDs are bound by the
selected remix; id zero is a send only when the remix uses SEND as its fallback.

RETURNS moves the wet audio to T8, before master FX1 and LEVEL when MASTER is
on, or directly to MAIN when MASTER is off. T1/T5 keep their engine FX2 slots
and can play dry sources. Muting either source must leave the shared wet tail
and other tracks' contributions audible. Master mute/LEVEL still affects the
whole master mix. During BusVerb warm-up, POST FADER retains the existing
DEL-ramp initialization sentinel until processing starts. The first active
call therefore seeds the current scaled send; a preceding unscaled firmware
initialization packet cannot excite the bus from a saved-muted T5. This adds
two instructions per warm-up call and none to the warmed path. It does not
clear a tank or alter a running tail. Cue and USB stem routing are consequently different from
host-local wet returns; this feature is not covered by an audio-identity claim.

RETURNS is inert off T8 and on core B. The new shared ring/stamp allocation is
`Y:0x30100..0x30208`; the old PR allocation conflicts with current code.
BusVerb uses private `Y:0xe00..0xe26`. The ledger declares ownership.
Live removal is not claimed seamless: queued stamped delay data can overlap
with resumed host printing during liveness expiry. The test rig locks the
assignment; live replacement requires separate qualification.

For existing projects, `tools/hw/ot_project.py host PROJECT REMIX` is a layout
conversion, not a T8-only edit:
it assigns all FX2 hosts/clients and resets effect defaults across parts/banks.
Use a copy and review scene locks, parameter locks and LFO destinations. Saved
stock T8 DELAY slot meanings are not automatically migrated to DLY/VRB return
controls. No user project was converted by this review.

## 3. How performance was measured

Two supplied firmware files are unpacked through their own boot pointers and
checksummed loader payloads. The test does not inject the current build's
window records. Baseline and candidate run on the same hashed `dsp_host`,
with the same deterministic asymmetric stereo input, controls, 16-frame
blocks, splits and automation. Four instances run together: BusVerb and SEND
on core A, BusDelay and SEND on core B.

The authoritative meter is the difference in `getInstructionCounter()` per
block, including emulated DSP DO-loop bodies. The separate per-instance console
summary counts interpreter calls and is unsuitable for this comparison.
Wall-clock render duration is not used as a DSP performance measure.

For the fixed cases below, 8,192 blocks are rendered and the first 512 are
excluded **only from performance statistics**: 7,680 blocks / 122,880 stereo
sample frames are measured. Audio equality includes every frame, including
startup. The means include one SEND per core, block setup and the delay pad;
they exclude the real stock dispatcher/mixdown, other tracks' effects, memory
contention and device I/O. A percentage below uses that measured harness-core
baseline as its denominator, not the chip's frame budget.

| Fixed case | Core | Before instructions/frame | After | Change | Change / measured baseline | Peak retained block before → after |
|---|---|---:|---:|---:|---:|---:|
| Delay CLEAN | B | 805.687500 | 799.687500 | −6 | −0.7447% | 12,891 → 12,795 |
| Delay GRAIN, four grains | B | 1,454.687500 | 1,270.687500 | −184 | −12.6488% | 23,275 → 20,331 |
| Delay GRAIN, two grains | B | 1,176.750000 | 1,078.750000 | −98 | −8.3280% | 18,828 → 17,260 |
| Delay REVERSE | B | 881.687500 | 879.687500 | −2 | −0.2268% | 14,107 → 14,075 |
| Reverb MODE 1, SHMR 0 | A | 1,024.288086 | 913.062500 | −111.225586 | −10.8588% | 16,689 → 14,609 |
| Reverb MODE 1, SHMR 127 | A | 1,024.288086 | 1,027.288086 | +3 | +0.2929% | 16,689 → 16,737 |

A frame here is one left/right sample pair. MODE 0 shimmer-off gives the same
measured mean as MODE 1; MODE 2's saving is 111.224365 instructions/frame.
The small non-integer reverb savings reflect phase-dependent branches in the
original path. Shimmer automation averages a saving of 65.795721, but that
number depends on this particular schedule and is not a general average.

Static loop pricing is a different measurement: four-grain GRAIN changes from
975 to 777, two-grain from 669 to 563. These word-span model values omit
block setup and the DMA pad; they must not be mixed with the table above.
No conversion of either measure into physical DSP utilization is justified.

An independent repeat of all six fixed pairs reproduced every meter-file byte
and all four audio hashes exactly. Enhanced receipts now store the exact
command, input and script hashes, integer instruction totals and denominator.
For example, the four-grain delay measurement is 178,752,000 → 156,142,080
instructions over 122,880 frames; it is not a rounded timing estimate.

The optional routing is additional work. The RETURNS mixer loop costs 12
executed instructions per stereo frame with MASTER on and 17 with MASTER off,
plus setup/smoothing. The 12-case fallback comparison measures selected
POST FADER/RETURNS engine paths **without a live RETURNS instance**; it is not
the net cost of the active integrated rig. There is no measured physical
before/after DSP or ColdFire utilization for the combined feature yet.

## 4. Regression evidence and its limits

| Check | Observed result | Boundary |
|---|---|---|
| Original vs optimized DSP | 79/79 cases, all four raw 24-bit streams byte-identical; 17 positive controls pass | 36 four-grain delay + 36 two-grain delay + 7 reverb; specified inputs and histories only |
| Adversarial audio and state | Three additional comparisons pass | Four/two-grain delay and reverb; details below |
| Whole/split fallback | 12/12 exact comparisons and eight controls pass | Modes 0/1/2 × splits 0/1/7/15; RETURNS selected but inactive |
| Held-note decoding | Eight renders + seven controls pass for each grain count; final four-grain image rerun passes | Tagged/untagged notes 0/72/84/96; two-grain integration run precedes the independent warm-up fix; old faulty image fails the negative control |
| ColdFire send hook | 2,048 installed-image + 4,096 synthetic bound-ID cases pass | Builder stubbed in the microtest; synthetic IDs 33/34/35/39 are not full 64-ID firmware acceptance |
| RETURNS DSP arithmetic | 212 exact cases pass | All 128 gain targets, MAIN/MASTER math, rotations, fresh/stale/once-only stamps, off-track/core guards; isolated mixer model |
| Full firmware audio | Ten original fixtures pass | Real builder/DSPs, stock OT mute semantics, MASTER on |
| Sounding-host startup | Four additional fixtures pass on the final image | T1/T5 × muted/audible, immediate input; both muted wet buffers and MASTER output exactly zero across 803 compared blocks |
| Mute continuity | T1/T2/T5 mutes preserve 803 compared non-silent tail blocks exactly | About 0.291 s of compared tail, not a long-tail soak |
| Other-source gain | T7 mute/LEVEL zero/solo exclusion leaves the T2 return exact | Silent T7 still has an original send; send-knob-to-zero control changes the return |
| New excitation | Continuously sounding T2 remains present at its SEND input but produces zero wet after mute/warm-up | SEND client; sounding host coverage is recorded separately below |
| Tool and structural checks | Ten image-extraction tests, eight cost-accounting tests, seven init-register checks and docs checks pass | Does not replace hardware timing or CI's broader build checks |

The 79-case matrix includes all delay modes plus unknown-mode fallback,
parameter endpoints, every valid grain size, five pitch points, several
scatter/density combinations, repeated buffer wraps, silence/startup/tails,
mode/knob automation and selected split positions. Reverb covers all modes,
active shimmer and interrupted SHMR/SHFT/MODE automation. These are exact
comparisons, not just an inaudibility threshold or matching peak/RMS values.

The three supplemental runs each cover 16,384 blocks / 262,144 stereo frames
(about 5.94 seconds): full-scale signed DC, alternating and one-LSB inputs,
all four sources fed, dirty initial X scratch, and parameter/mode automation.
Both delay line stores demonstrably hit both saturation limits. The original
L/R control records agree through 11,314 distinct vectors with four grains and
10,786 with two. Reverb completes four fade-outs to exact zero while dormant
filters and phases remain active, then resumes shimmer at SHMR 1 and 127.

All four audio streams and the target core's final Y:$00000..$3ffff
(262,144 words, covering the reviewed bus regions) match exactly. Every block's 132 target X-state words are compared. Allowed differences
are explicitly restricted to the repurposed delay cache (`$4c..$57`, or
`$4c..$51` with two grains), and reverb `$14/$38` while **both** glided shimmer
gains are zero. No other state differences occurred. This samples state at
block boundaries and Y at the end; it is not a trace of every intermediate
memory write or a test of arbitrary corrupt runtime/warm-up tags.

Four defects in integration/testing were found and corrected: HOSTGUARD
clobbered the dispatcher's A-register split flag; a tagged REV word left stale
accumulator sign bits before held-note shifting; a legacy dumper could overlay
new window code onto an old image; and an unscaled initialization packet seeded
BusVerb's DEL ramp while its warm-up path prevented that ramp from advancing.
The last defect let a saved-muted, immediately sounding T5 excite the wet bus.

The startup failure was retained, not waived as an expected tail. Delaying
source onset by 400 ms made the old image pass, isolating initialization from
ongoing gain decoding. The fix keeps the DEL sentinel during warm-up; it never
resets the ramp after warm-up. The required regression uses immediate onset,
checks both wet-only buffers and tagged-zero sends, and requires nonzero dry
host audio. Unmuted counterparts must excite both buffers. The pure DSP
optimizations were not implicated. Earlier integrated image `7b7c545c…` is
superseded by the startup-fixed image listed below.

The fixes have causal regression controls. The ColdFire microtest was also
changed to unpack its runtime from the supplied image instead of mapping
an ambient `runtime.bin`. Earlier results from contaminated window-image
extraction are invalid evidence and are not counted here.

## 5. Reproduction and provenance

For the original review, use the tools at `d45d80c4` on the retained backup
branch, the user's own OS 1.40C, the pinned source revisions above, and
identical build options. The 29 October rebase checks are recorded separately
below; they use the rebased tools and updated emulator pin. Keep every image under a distinct
name before the next build. Do not restore a firmware file while leaving
incompatible ambient build metadata and then invoke a legacy gate.

```sh
mkdir -p out/bus-audit
# Export both upstream engine sources without changing the checkout.
git show f8141428:modules/busdelay/delay_server.asm > out/bus-audit/original-delay.asm
git show f8141428:modules/busverb/reverb_server.asm > out/bus-audit/original-reverb.asm
BUILD=79 DLSRC=out/bus-audit/original-delay.asm RVSRC=out/bus-audit/original-reverb.asm make bus REMIX=bus
cp out/mainos_bus.bin out/bus-audit/original.bin
git show 3a0b2d22:modules/busdelay/delay_server.asm > out/bus-audit/optimized-delay.asm
git show 3a0b2d22:modules/busverb/reverb_server.asm > out/bus-audit/optimized-reverb.asm
BUILD=79 DLSRC=out/bus-audit/optimized-delay.asm RVSRC=out/bus-audit/optimized-reverb.asm make bus REMIX=bus
cp out/mainos_bus.bin out/bus-audit/optimized.bin
python3 tools/verify/verify_bus_dsp_identity.py out/bus-audit/original.bin out/bus-audit/optimized.bin --engine all --out out/bus-audit/identity
```

The two-grain pair uses the same explicit sources and build settings:

```sh
python3 - <<'PYTHON'
from pathlib import Path
import sys
sys.path.insert(0, "tools")
import toolpath
from remix.grains import roll
root = Path("out/bus-audit")
for name in ("original", "optimized"):
    (root / f"{name}-delay-2grain.asm").write_text(
        roll((root / f"{name}-delay.asm").read_text(), 2))
PYTHON
BUILD=79 DLSRC=out/bus-audit/original-delay-2grain.asm RVSRC=out/bus-audit/original-reverb.asm make bus REMIX=bus
cp out/mainos_bus.bin out/bus-audit/original-2grain.bin
BUILD=79 DLSRC=out/bus-audit/optimized-delay-2grain.asm RVSRC=out/bus-audit/optimized-reverb.asm make bus REMIX=bus
cp out/mainos_bus.bin out/bus-audit/optimized-2grain.bin
python3 tools/verify/verify_bus_dsp_identity.py out/bus-audit/original-2grain.bin out/bus-audit/optimized-2grain.bin --engine delay --grains 2 --out out/bus-audit/identity-2grain
```

Leave the remix's normal four-grain substitution setting unchanged when using
these already-transformed files. `--grains` records a declared configuration;
it does not infer the grain count from the image.

Supplemental state checks use the same pinned pairs:

```sh
python3 tools/verify/verify_bus_dsp_state.py out/bus-audit/original.bin out/bus-audit/optimized.bin --engine delay --grains 4
python3 tools/verify/verify_bus_dsp_state.py out/bus-audit/original-2grain.bin out/bus-audit/optimized-2grain.bin --engine delay --grains 2
python3 tools/verify/verify_bus_dsp_state.py out/bus-audit/original.bin out/bus-audit/optimized.bin --engine reverb
```

All four images were reconstructed from these pinned sources through the
reviewed builder and matched the original measured images byte for byte.
The integrated image was rebuilt after the startup correction, frozen under
a distinct filename, and used for the final integration checks. Build and
check that optional integration separately, using an owned structural project
template:

```sh
BUILD=79 make bus REMIX=send-return-poc
cp out/mainos_bus.bin out/bus-audit/integrated.bin
python3 tools/verify/verify_bus_dsp_identity.py out/bus-audit/optimized.bin out/bus-audit/integrated.bin --returns-fallback --remix test/send-return-poc --out out/bus-audit/fallback
python3 tools/verify/verify_postfader_hook.py test/send-return-poc --image out/bus-audit/integrated.bin --receipt out/bus-audit/hook.json
python3 tools/verify/verify_postfader_dsp.py test/send-return-poc --image out/bus-audit/integrated.bin --grains 4 --out out/bus-audit/notes
python3 tools/verify/verify_returns.py test/send-return-poc --image out/bus-audit/integrated.bin
python3 tools/verify/verify_postfader.py test/send-return-poc --image out/bus-audit/integrated.bin --project "$OT_PROJECT"
python3 tools/verify/verify_postfader_hosts.py test/send-return-poc --image out/bus-audit/integrated.bin --project "$OT_PROJECT"
```

The hook microtest checks the current build's symbol/layout metadata against
the supplied image and extracts executable bytes from that image. Run it
before building another selection. The firmware gates copy the template into
owned scratch directories; they do not modify the source project. Set
`OT_PROJECT` to an existing local project directory. Missing project fixtures
are skips, not successful audio acceptance.

The original run receipts are local files under `out/optimization/`:
`identity-4grain-image-bound/results.json`, `identity-2grain-image-bound/results.json`,
`identity-reverb-image-bound/results.json`, `returns-fallback-startup-fixed/results.json`,
`postfader-note-startup-fixed-4grain/results.json` and
`postfader-note-final-2grain/results.json`. They contain image and
host hashes, executed-memory hashes, per-case output hashes and measured counts.
The meters and logs remain beside them. The ten-case firmware receipt is
`out/review/measurement/postfader-startup-fixed-receipt.json`.
The original sounding-host receipt is now
`out/rebase-20261029/previous-postfaderhosts/results.json`; the earlier
failed immediate-onset cases remain under
`out/postfaderhosts-startup-immediate/`. The supplemental receipts are `out/optimization/state-{delay-4grain,delay-2grain,reverb}/results.json`;
the independent repeat is `out/review/measurement/repeat-enhanced/results.json`.
Firmware and memory dumps are not committed. Generated audio and full local
receipts remain in ignored `out/`; the measured numbers and identities in this
document are retained in Git.

| Artifact | SHA-256 |
|---|---|
| Original four-grain image | `07d5c6a91df246210c2dc8b9f41804b3bf71da0ab2423a23a2eaf4e5ace9b8b9` |
| Optimized four-grain image | `afb7ceb7c212f1bc7cb814f6808b5e070ee2286dcf179facbb39b7e79a847528` |
| Original two-grain image | `abcedc1a40ef6d46e20316540fd7e9741353f90bfcfd981e2b7e83fa3ca94ed2` |
| Optimized two-grain image | `d7e1bd10c70d4ed0fc7c1a37ed2f691e3e8f3562777acc96da19aea063f3c71d` |
| 26 October integrated four-grain image | `9317770bbf847a94f47508cb087681c0822517d3730868cc87c0f047d59633e8` |
| Superseded integration image; startup negative control | `7b7c545cd11e426bef893743095b989c59d320ace51fa1eb4b999ca1b4134d4a` |
| 26 October measured DSP host | `e936529aadccbc623018f191eff8d30aab08e32be73f52c2c75d834a7b216e8f` |

## 6. Rebase onto current upstream, 29 October 2026

The feature branch was rebased onto upstream `main` at
`bc1445238541e120fbb0ad72e90c89caf97f4d24` (114 commits after the previous
synchronization). The original published state remains on the backup branch
above. `git range-diff` confirms equivalent feature patches; the only manual
conflict resolution kept both additions to `TRAPS.md`. The bus DSP sources,
POST FADER/RETURNS implementation and feature-specific verification scripts
are unchanged.
The equivalent optimization commit is now `04db7e3a`; the rebased startup
fix is `a61fd750`. The tested source head before this documentation update
is `9c789f5a`.

Unlike the earlier documentation-only synchronization, this upstream update
changes the builder, selected firmware modules and emulator. In particular,
MUTE MODES moves its shadow state into DRAM, USB changes its buffer handling,
and DSP56300 moves from `8ccdd843` to `8b731966`. The new interpreter changes
DO-loop termination behavior. Earlier results therefore were not accepted
as sufficient qualification of the rebased integration image.

The new toolchain was built privately in this worktree, leaving the shared
toolchain untouched. The pinned vendor test runner, assembler checks,
18 focused unit tests and seven init-register checks pass. The port's CTest
run passes eight applicable tests; `repitch-patch` explicitly skips because
this is not a REPITCH image. Documentation checks also pass.

| Rebase artifact | SHA-256 |
|---|---|
| Integrated four-grain image | `256de5d1819a0039056b0fdb9abeccfb1523914f1b0d9ec654db8f4e8827bdea` |
| DSP host | `47de4ff0859681905b4e475d5036be8f5ed1fed9cbe2fed7ce1b08f8657d8da3` |
| DSP assembler | `23047635db619ebd89dd3ae2bb1f3bf74e295f70dc7c56a62acfeb8c3db9ed6e` |
| ColdFire/DSP port | `343a3643214a84310a66a374897ee2980304c52bf0ff5cdb19a07bc4374e616f` |
| DSP vendor patch | `05a175b0e864e6a3c34b50a6b2749b4b0e338d092f9236c272d596b672f5a4bf` |

All four plain comparison images rebuilt byte-for-byte identically to the
original image hashes above. Fresh checks on the new toolchain establish:

| Check | Rebased result |
|---|---|
| Pure audio identity | 79/79 cases and all controls pass |
| Comparison with historical runs | All 158 complete meter files and 632 output hashes match exactly; headline instruction totals and percentages are unchanged |
| Adversarial state | All three runs pass; their audio, sampled X state and final Y-range hashes also match the historical runs |
| Selected fallback paths | 12/12 exact comparisons and eight controls pass |
| Held notes, four grains | Eight renders and seven controls pass |
| Installed ColdFire hook | 2,048 installed-image and 4,096 bound-ID cases pass |
| RETURNS arithmetic | 212 exact cases pass |
| Full firmware tails and sends | Ten fixtures / 35 checks pass; other-source returns and T1/T2/T5 mute tails remain exact across 803 non-silent blocks; active muted T2 adds no wet audio |
| Sounding-host startup | Four fixtures pass; muted T1/T5 have zero wet buffers and late MASTER output despite sounding dry audio |

The unchanged performance table remains a harness instruction measurement,
not a physical DSP-load claim. The new image is qualified only for the checks
listed here; the hardware and routing limits below remain in force.

Fresh results are retained under
`out/rebase-20261029/`, with build logs and source exports beside them.
The measurement receipts are `identity4/results.json`, `identity2/results.json`
and `measurement-comparison.json`; state checks are in
`state-{delay4,delay2,reverb}/results.json`. Integration receipts include
`returns-fallback/results.json`, `postfader-notes/results.json`,
`postfader-hook.json`, `postfader-hosts-results.json` and the combined
14-fixture receipt `postfader-rerun-results.json`.
Historical firmware cards and receipts were preserved in
`previous-postfaderverify/` and `previous-postfaderhosts/` inside that directory;
earlier failure artifacts remain intact.

## 7. Acceptance still required

The evidence supports equivalence for the measured DSP cases. It does not
establish absence of every functional regression or qualify the changes for
hardware release. Keep pure optimization review separable from the intentional
routing changes so the original author can accept either independently.

Before hardware acceptance, compare upstream and candidate on the same unit,
project, samples, gain settings and workload. Record firmware/project hashes,
unit/OS identity, meter reset boundaries, per-core timing and synchronized audio.
Repeat in alternating order so warm-up/history and load drift are visible.
Use the existing [hardware workflow](HARDWARE_TESTING.md) and
[load measurement tools](COSTS.md), retaining mean, distribution and peak values
rather than reporting only the best observed result.

Required scenarios include light and heavy FX1 load, all delay/reverb modes,
SHMR zero/active/transitions, two/four grains, shortest/longest splits, host and
client mutes, high feedback with long silence, mode changes during tails,
MASTER on/off, and stereo impulse timing. Include the historical STATIC-T1,
hard-left zero-burst/DMA reproduction for at least paired ten-minute captures.
Preserve the pad until those timing measurements justify any separate change.

Active-return splits, alternative MUTE MODES, cue-only use, USB stem semantics,
scene XLV, and live return activation/removal need explicit acceptance before
being advertised. An emulator hang, unexpected state/audio difference, changed
remaining-source gain, lost tail, dropout, deadline overrun or corruption is a
failure to investigate, not a difference to average away.

CI's reached gates and build-identity checks also remain part of upstream
review. Repository policy delegates whole-remix/reach/refhash passes to CI;
this local review ran focused gates. No image was flashed as part of this review.

## 8. Further optimization review — 31 October 2026

This follow-up measures configuration costs on the already optimized image and
ranks further candidates. It changes no DSP code. Candidate savings below are
source-derived bounds, not measured improvements or hardware CPU percentages.

### Reverb configurations: measured

Twenty-one configurations use the section 3 harness and the section 6 toolchain,
at source `aaadcc2b`. The frozen input image is `optimized4.bin`, SHA-256
`afb7ceb7c212f1bc7cb814f6808b5e070ee2286dcf179facbb39b7e79a847528`.
Every run renders 8,192 blocks, retaining 7,680 blocks / 122,880 stereo frames
for instruction statistics. Core A contains BusVerb and one SEND; core B
contains CLEAN BusDelay and one SEND. This is the pure DSP image, without the
optional POST FADER/RETURNS paths.

Default reverb settings are SIZE 100, SHMR 0, SHFT +12, WET 127, PLATE,
TONE 64, DIFF 80, GATE 0, DLY 127 and TIME 64; its host DEL/REV are zero.
SEND A uses REV 100, SEND B uses DEL 100, and delay repeats also feed reverb.
Each row changes only the stated controls. The same deterministic input includes
noise, tones and silence. No parameter automation or block splits occur here.

| Reverb configuration | Core-A instructions/frame | Maximum retained block |
|---|---:|---:|
| ROOM, PLATE or BIG; SHMR 0 | 913.062500 | 14,609 |
| ROOM or PLATE; SHMR 127 | 1,027.288086 | 16,737 |
| BIG; SHMR 127 | 1,027.286865 | 16,737 |
| PLATE; SHMR 1 or 64 | 1,027.288086 | 16,737 |
| PLATE; DIFF, SIZE, TIME or TONE at 0 or 127; SHMR 0 | 913.062500 | 14,609 |
| PLATE; GATE 8, 20 or 127; SHMR 0 | 913.000000 | 14,608 |
| PLATE; SHMR 127, SHFT −12 | 1,026.661051 | 16,727 |
| PLATE; SHMR 127, SHFT +24 | 1,027.663900 | 16,743 |

ROOM, PLATE and BIG use the same eight-line tank, four input allpasses, two
bloom allpasses and two in-loop allpasses. They change constants and tap
lengths rather than the number of processors. BIG is therefore not a heavier
algorithm. Lower DIFF does not remove allpasses; shorter TIME/SIZE does not
remove tank lines; a closed gate does not suspend the tank.

Shimmer is the meaningful load switch: SHMR 0 saves 114.225586 instructions/frame
against active PLATE, or 11.1191% of that active harness-core workload. Conversely,
active shimmer costs 12.5102% more than shimmer-off. The tested nonzero amounts
1, 64 and 127 cost exactly the same. A turn to zero must finish its glide before
the existing fast path engages. The small SHFT differences are under 0.1%
between the tested endpoints; selecting a different interval is not a useful
load reduction.

All six mode × SHMR 0/127 cases were independently repeated with fresh input
generation and image extraction: every meter byte and all four audio hashes
match. Seven controls confirm identical inputs, unchanged core-B meters,
nonzero reverb output, effective control changes, reproduction of the previous
PLATE reference's audio and instruction totals, and an untouched ambient
firmware image. These checks validate the cost comparison, not a new DSP change.

### Split calls matter more than the reverb character

Three additional runs split every 16-frame block at frame 1, 7 or 15, with the
same default PLATE/SHMR 0 settings. All three split positions have the same cost:

| Harness core | Whole block instructions/frame | Split block | Increase |
|---|---:|---:|---:|
| A: BusVerb + SEND | 913.0625 | 979.0000 | 65.9375 / 7.2216% |
| B: CLEAN BusDelay + SEND | 799.6875 | 1,346.3125 | 546.6250 / 68.3548% |

BusDelay's 8,192-NOP pad runs per live proc call, so a split block pays it twice.
The second pad accounts for 512 instructions/frame of core B's increase; the
remaining 34.625 comes from other extra call work. Reverb also repeats setup.
These runs split all four harness instances on every block. They do not measure
the frequency of splits in a real project or imply this increase across a song.
Server audio differs between whole and split renders: this is a cost comparison,
not an equivalence claim. Existing baseline/candidate split equivalence remains
the relevant regression check. Moving control glides to once per block would
itself change the existing split behavior.

### Prioritized candidates

The first four reverb candidates aim to preserve the current output and state:

| Candidate | Source-derived opportunity | Conditions and proof needed |
|---|---|---|
| Specialize the eight low-cut updates at exact-zero coefficient | Gross 48 instructions/frame | Test the actual glided coefficient. Keep subtraction of the frozen, possibly nonzero filter state and the existing limiting point. TONE's target alone is insufficient. |
| Specialize the GATE 0 envelope | Gross 14 instructions/frame | Keep the counter/retrigger state and both gate multiplies: `0x7fffff` is not exact unity. Preserve transitions back to an active gate. |
| Specialize the six tank lines with fixed zero input weight | Gross 12 instructions/frame | Retain their feedback gains, table layout, state writes, pointer advancement and required instruction spacing. The two driven lines keep the original arithmetic. |
| Inline the four input allpass calls | At most 8 instructions/frame | Keep identical arithmetic and AGU spacing; replacement padding may consume part of the saving. Check program-space fit. |
| Precompute the pinned LFO rate and eight increments | Gross 34 instructions/call, or 2.125/frame unsplit | Derive exact fixed-point constants, preserve stored values and existing phase-update gating. This is a small addition. |

The first four total **82 instructions/frame before guards and padding**, about
9.0% of the measured shimmer-off core-A workload, or 8.0% with shimmer active.
They are not an implemented or guaranteed speedup. The LO and gate opportunities
apply to the default control state; their benefit changes with settings.
These counts do not support a promise of another 20–30% reverb reduction.
General MODE caching is lower priority: some copied slots are overwritten with
derived TIME/LFO values each call, so unchanged MODE does not make the copy
redundant without further changes.

Three further candidates serve the bus as a whole. The SEND alternatives overlap;
their savings must not be added together for the same client:

- **Settled sends at any gain:** when both actual per-sample steps are zero
  after existing setup, hold the two gains in registers and omit both ramp
  update sequences. The sample body can fall from 25 to 15 instructions,
  before the once-per-call predicate and two gain loads. This also benefits
  audible, steady sends. Verify signed multiply encoding and preserve the
  stored gain values, count handling and transient-ramp path.
- **Settled-zero sends:** after normal ramp setup, a SEND with both running
  gains and both steps exactly zero can avoid its 25-instruction sample body,
  less dispatch and required pointer handling. One settled-zero destination
  offers 10 instructions/frame before overhead. Preserve housekeeping and
  original send participation/counts, including the POST FADER tag. A muted
  source can stop contributing while other sources retain exactly the same
  normalization and both engines continue their tails. Do not gate on the
  target knob or mute alone, because an existing ramp may still be audible.
- **Zero-gain grains:** skip a grain's audio reads, interpolation and addition
  when its computed window gain is exactly zero, retaining all phase, PRNG,
  latch, accumulator and cache evolution. The shipping geometry has 21 such
  instructions/channel/grain: 42 gross for a closed stereo grain. Four closed
  grains offer 168 gross, but guards and loop-end handling reduce this; dense
  settings could become slower. Benchmark sparse and dense workloads separately
  before choosing a dispatch strategy. This retains four grains rather than
  changing the algorithm to two.

### Largest opportunity: requalify the delay wait on hardware

The unchanged pad alone is 512 instructions/frame in whole blocks: 64.0% of the
measured CLEAN core-B workload and 40.3% of four-grain GRAIN. These are shares of
the harness instruction count, not safely recoverable CPU budget. For scale,
halving the pad would remove 256 instructions/frame, equivalent to 32.0% and
20.1% of those respective workloads **if hardware timing allowed it**. Redundant
waiting on a second call in the same frame is another hypothesis to test.

The [failure record](FAILURE_MODES.md) explicitly leaves open whether the later
REP-to-DO conversion removed the original reason for this pad. It also records
failed DSR1/DCR1 polling and frame-end/idle-hook attempts. Those approaches must
not be presented as established fixes. Qualify the current interruptible build
with paired timing/load measurements and at least ten-minute hard-left burst
captures, including light/heavy FX1, different modes, splits and sounding hosts.
Keep the current pad until that evidence establishes a safe alternative.
Material delay-loop speedups also need this timing check even with the pad
unchanged: less computation advances the following read-back copy.

Halving the reverb sample rate, reducing its eight tank lines, dropping modulation
or interpolation, or reducing four grains to two would change the sound or
behavior. They belong to optional alternative algorithms, not this exact-output
optimization. Suspending a shared engine on track mute, WET 0 or a closed gate
is also unsuitable: its state and tails may still matter later. A build without
shimmer removes the ability to enable it and is a feature tradeoff.

Local reproducibility receipts are retained under `out/profile-20261031/`:
`profile_busverb.py` with `results.json`, and separate repeat/split scripts and
receipts. The main receipt includes every command, setting, integer total,
denominator, input/audio/meter hash and executable provenance. SHA-256 values:

- Main 21-case receipt: `c36f1d70caf16b485870ebffd41c13b93a2ae01718d2e544981544a4cae2b388`.
- Six-case repeat receipt: `819fc05bc5d81e53b8a5b1df7a2b1633762000c972c0fcd5a441320dadb90124`.
- Three-case split receipt: `b3008a606a71e42d544cc383a333566104cee92fc6db693dc1a0002fc465d230`.

At the time of this profile, the recommended next work was the small exact-output
reverb specializations and settled-zero SEND paths, each compared against this frozen implementation for
audio, persistent state, automation, splits and instruction cost. Investigate
the DMA wait separately on hardware; it offers the largest potential reduction
and has a different acceptance burden.


## 9. Second optimization pass — 31 October 2026

This pass uses `db3b62c9` and the 29 October optimized images as its immediate
reference. The earlier measurements in this document remain historical; the
new savings are additional to that first pass. Sam Banks remains the author
of these engines. This is an optimization of their implementation, with the
original algorithms, fixed-point audio and persistent musical state as the
contract.

### Exact work removed

- **BusVerb:** precompute the pinned RATE and first two LFO increments; inline
  the four input allpasses while retaining address-generator spacing; combine
  eight independent allpass state stores with multiplies; specialize the six
  zero input weights. At an exactly zero **glided** LO coefficient, retain and
  subtract its possibly nonzero frozen history. At GATE 0, omit redundant
  envelope arithmetic but keep its counter, retrigger history and output
  multiplies. Q23 full-scale is not mathematical unity, so those multiplies
  cannot simply be removed.
- **SEND:** dispatch only after the original coefficient snaps and ramp-step
  calculations. Preserve registration and housekeeping on every call. Moving
  gains use the original ramp with two parallel loads; settled gains use
  separate both/one/neither-active paths. The inner loops execute 23, 13, 9 or
  2 instructions per sample respectively, versus 25 before dispatch/setup.
  Zero targets alone never select the silent path; the actual steps and gains
  must be zero. POST FADER membership remains independent of scaled amplitude.
- **BusDelay:** wrap the aligned left line using hardware modulo addressing,
  restoring the linear modifier on exit. Keep the differently aligned right
  line's original wrapping. Cache TIME's integer/fraction decomposition only
  when the actual TIME/FDBK/TONE/PING steps are all zero; recompute the cache
  for every eligible call, including split calls. Combine independent GRAIN
  loads/multiplies and remove redundant register moves. The new raw scratch
  words are `$6e` (step mask), `$6f` (integer lag), and `$7e` (fraction); the
  RETURNS reservation at `$65` is not reused. Below DENS 96, a separate GRAIN
  path omits channel tap/interpolation/product work only when that grain's
  computed window gain is exactly zero. Phase, random/latch evolution and all
  control-cache writes still run. DENS 96–127 uses the unguarded path: measuring
  all eight density buckets found that guarding bucket 6 was a regression.

No sample-rate, tank-line, interpolation, filter, feedback, modulation or
shipping grain-count reduction is part of this pass. Zero SEND input does not
suspend either server or clear a tail. The 8,192-instruction delay wait remains
unchanged; faster computation still changes real timing and requires hardware
qualification.

### Verification method

`verify_bus_dsp_identity.py` compares all 24 bits of each rendered output and
records the executed instruction counts from image-extracted DSP code. The
new `verify_bus_fastpaths.py` also captures all 132 instance-state words after
every block, plus all 262,144 final Y words of the selected core, with no address
exclusions. The standalone host keeps P separate from X/Y at the hardware's
shared-window addresses (`dsp_host.cpp` constructs memory with bridge `0x200000`
and shares X/Y between cores). This capture therefore does not inspect P-word
immutability or prove the physical aliasing/timing behavior. Image extraction,
assembler checks and full-firmware routing fixtures provide separate evidence.
An initial attempted P-via-Y immutability check failed even for correct images;
that incorrect model was removed, rather than excluding mutable memory from
the comparison. Its diagnostic receipts are retained.

The adversarial state gate retains the original unoptimized image as a separate
oracle. New delay scratch is checked against explicit invariants, not ignored:
the step mask equals the OR of the four real steps; settled lag/fraction equal
the clamped Q8 TIME decomposition, otherwise the cache must retain its previous
value. The earlier GRAIN cache and dormant-shimmer exceptions remain bounded
as described above. Dirty startup, saturation of both signs, automation and
unequal split calls exercise these checks.

Instruction counts are work performed by the emulator, not elapsed benchmark
time, physical DSP cycles, or a measured percentage of the Octatrack's total
CPU. The harness includes one server and one SEND per core. Setup, dispatch and
an unchanged wait therefore matter alongside the sample loops.

### Measured instruction savings

The immediate reference is the already optimized 29 October image. Whole-block
cases below retain 7,680 blocks / 122,880 stereo frames after warm-up. Counts
include the server and one SEND on that core, and setup/dispatch/wait work.
The grain-density sweep fixes TIME 100, SIZE 1, PTCH 64 and SCTR 127; it is
separate from the default TIME 40 comparison.

| Configuration | Core | Before instructions/frame | After | Additional reduction |
|---|---|---:|---:|---:|
| Reverb, SHMR 0, TONE 64, GATE 0 | A | 913.0625 | 816.1250 | 10.62% |
| Reverb, SHMR 127, TONE 64, GATE 0 | A | 1027.2881 | 930.3506 | 9.44% |
| CLEAN delay | B | 799.6875 | 754.3125 | 5.67% |
| REVERSE delay | B | 879.6875 | 834.3125 | 5.16% |
| GRAIN, four grains, DENS 127 | B | 1270.7500 | 1210.3750 | 4.75% |
| GRAIN, four grains, DENS 0 | B | 1270.7500 | 1099.7035 | 13.46% |
| GRAIN, two grains, DENS 127 | B | 1078.8125 | 1026.4375 | 4.85% |
| GRAIN, two grains, DENS 0 | B | 1078.8125 | 972.1016 | 9.89% |

Matching the new cases to the original-reference measurements in section 6
also gives cumulative reductions: reverb with SHMR off **20.32%**, CLEAN
**6.38%**, REVERSE **5.37%**, default dense four-grain GRAIN **16.80%**, and the
DENS 0 / SIZE 0 / PTCH 64 grain case **24.41%**. The intermediate image's input,
audio hashes and meter values match across the two receipts before composing
these comparisons. These are reductions of the measured per-core harness
workload, not percentage points of the instrument's total DSP utilization.

ROOM, PLATE and BIG still have effectively the same processing cost when the
other controls match. Active shimmer adds about 114.226 instructions/frame;
its nonzero amount does not select a cheaper algorithm. The new specializations
make LO/gate activity matter too. With SHMR 0 in PLATE:

| TONE | GATE | Candidate core-A instructions/frame |
|---:|---:|---:|
| 64 | 0 | 816.1250 |
| 64 | 8 | 831.0625 |
| 127 | 0 | 865.1250 |
| 127 | 8 | 880.0625 |

The LO-active case costs another 49 instructions/frame, and the active gate
case another 14.9375 including setup. Choosing a reverb character is therefore
not a significant load lever; shimmer and these active processing paths are.
The tests drive the LO state before freezing it and close an enabled gate
before disabling it, so equality does not rely on never-excited state.

### Sparse GRAIN: mean and peak tradeoff

Both two- and four-grain images were compared at all eight DENS buckets. The
initial guarded bucket 6 lost 9.298 instructions/frame with four grains and
7.315 with two against the intermediate candidate. The final code routes
buckets 6 and 7 to the dense reader. Bucket 5 retains a small average win
against that intermediate image: 8.031 / 2.016 instructions/frame for four/two
grains in this fixture.

A grain's latched window can remain open during a density transition. When all
windows are open, guards cost 24 / 14 instructions/frame more than the
intermediate candidate without sparse skipping. This is an explicit peak-cost
tradeoff for lower average work at sparse settings. Against the immediate
pre-pass reference, **every measured density-sweep block still improves**:
the smallest paired saving is 502 / 598 instructions per 16-frame block.
Maximum observed blocks fall from 20,332 to 19,830 with four grains, and from
17,261 to 16,663 with two. This finite sweep is not a proof of all possible
runtime histories or chip deadlines.

The conservative source-word pricer reports BusVerb 1039 for its dearer LO
arm / 989 for LO zero, SEND 23/13/9/9/2 by path, and four-grain delay 805 at
its worst modeled path. It includes the sparse all-open alternative and
conservatively counts forward-skipped work; it is not interchangeable with
executed instructions or measured hardware cycles. Pricing markers assemble
byte-for-byte identically and the two-grain lever covers both reader pairs.

### Final qualification and reproducibility

| Check | Result | Boundary |
|---|---|---|
| Existing audio matrix | 43 four-grain + 36 two-grain pairs pass | All four raw24 outputs, startup, automation and tails |
| Adversarial state | Three 16,384-block pairs pass | Complete server X block and final Y; bounded scratch exceptions checked explicitly |
| Full-image fast paths | 30 plain + 38 routed pairs pass | Raw24 audio, complete selected X block and all Y words; gate closure/reset, frozen LO history and fractional/tagged sends |
| Density sweep | Eight buckets × two grain counts pass | All raw24 outputs plus mean, maximum and paired block costs |
| Isolated SEND | 24 pairs pass | Tagged transitions, fractions, saturation, per-block bus words and register contracts; housekeeping tested separately |
| Routing fallback | 12 mode/split pairs + eight controls pass | Equivalent plain/tagged inputs, no active return client |
| Held-note decoding | Eight renders + seven controls pass | Membership tags do not become a GRAIN note |
| Full firmware | Ten audio fixtures + four sounding-host startup fixtures pass | Actual LEVEL/mute/solo hooks and active independent returns |
| Installed POST FADER hook | 2,048 installed-image + 4,096 synthetic-ID cases pass | Stock builder stubbed in this focused hook test |
| RETURNS | 212 exact cases pass | Installed bytes/hook and arithmetic/ownership model |
| Focused unit checks | 47 tests pass | Includes cache-oracle fault injection, all-Y capture faults and both GRAIN substitutions |
| Init registers | Three plain-bus and seven integrated module inits pass | Static dispatcher contract |

The firmware fixtures retain original participation while a source is muted or
faded, verify an unchanged other-source return, and compare tails after T1/T2/T5
mutes. The measured tail comparison is 803 frames, about 0.291 seconds; it is
not a long physical decay capture. Four additional fixtures begin with a
sounding T1 or T5, already muted or unmuted, and check dry audio and both wet
buffers. The complete sequence passed through the workspace's artifact-retention
wrapper; successful generated cards were removed, while logs and receipts stay.

Builds use BUILD 79 and the same private toolchain recorded in section 6. The
strict normal four-grain and integrated builds pass the signed/unsigned multiply
audit, assembler/disassembler checks and memory placement. The plain image leaves
161 program words free on core A and 727 on core B; the sparse reader trades
213 program words for less work than the intermediate candidate. An integrated rebuild
is byte-identical. A final whitespace cleanup in the delay source is separately
assembled for two/four grains and plain/routed selection: all four code blobs
are identical to the tested snapshots. The source changes do not alter screens.
Broader whole-remix/reach/refhash checks remain CI work under repository guidance.
No hardware was flashed or measured in this pass.

Final local artifacts live under `out/optimization-20261031/`. Key receipts are
`final-identity4`, `final-identity2`, `final-state-delay4`, `final-state-delay2`,
`final-state-reverb`, `final-density4`, `final-density2`, `send-micro`,
`final-fastpaths-full-y`, `final-fastpaths-integrated-full-y`,
`final-fallback`, `final-notes`, and the `firmware-results.json`,
`postfader-hook.json`, `postfader-hosts-results.json`, `returns-results.json`,
`final-density-peaks.json`, `cumulative-measurement.json` and
`final-provenance.json` files. The instruction-measurement receipts record the actual input,
image-extracted payloads, executable hashes, commands and meter totals. Earlier
`pass1`, `pass2`, and failed instrumentation receipts are diagnostics, not the
final acceptance result. Proprietary images and audio remain untracked.

| Final image | SHA-256 |
|---|---|
| Plain four-grain | `214d86d8ab2fba32b3d5012067af13299571bc1deb4ae87712fffc7af9b830d7` |
| Plain two-grain | `cde0c439519d61a1f75f7e9e1a73eed601516fc304e606ef319023da9e3bb60e` |
| POST FADER + RETURNS, four-grain | `709b66bfa9b9606fa9bc2099bc82f63b8e0344c3763203c72c2f5077fba68730` |

To reproduce, build the immediate reference at `db3b62c9` and the candidate
separately using the pinned toolchain and the same selection/grain count as
section 5. Keep the original engine image for the state gate's L/R recurrence
control. The following commands illustrate the new gates; filenames stand for
those separately built images:

```sh
python3 tools/verify/verify_bus_dsp_identity.py before4.bin after4.bin --engine all
python3 tools/verify/verify_bus_dsp_identity.py before2.bin after2.bin --engine delay --grains 2
python3 tools/verify/verify_bus_dsp_identity.py before4.bin after4.bin --engine density
python3 tools/verify/verify_bus_dsp_identity.py before2.bin after2.bin --engine density --grains 2
python3 tools/verify/verify_bus_fastpaths.py before4.bin after4.bin
python3 tools/verify/verify_bus_fastpaths.py before-routed.bin after-routed.bin --post-fader
python3 tools/verify/verify_bus_dsp_state.py original4.bin after4.bin --engine delay --derived-delay-mask
python3 tools/verify/verify_bus_dsp_state.py original2.bin after2.bin --engine delay --grains 2 --derived-delay-mask
python3 tools/verify/verify_bus_dsp_state.py original4.bin after4.bin --engine reverb
python3 tools/verify/verify_send_fastpaths.py before-send.asm modules/send/send_client.asm --image after4.bin
```

`before-send.asm` is the SEND source from `db3b62c9`. The isolated test is now a
tracked tool so tagged-transition evidence can be reproduced without the local
scratch script. Constant `-pword` overrides cannot schedule tagged raw-word
changes in the full-image host; that limit is covered by the isolated wrapper
and the real firmware mute/fader tests instead of claiming unsupported host
behavior. The unchanged DMA wait and section 7's physical acceptance work remain
the boundary on release claims.

## 10. Separate half-wait DMA experiment — 31 October 2026

This is an opt-in hardware experiment on the optimized bus with POST FADER
and T8 RETURNS. The regular `modules/busdelay/delay_server.asm` retains its
8,192-NOP read-back pad. The experiment builds a separate source snapshot
with a 4,096-NOP pad through the existing `DLSRC` override; reverting the
experiment does not undo the audio-preserving optimizations in section 9.
It changes when the following output copy can run, not the delay's intended
audio arithmetic. That timing change is precisely what needs a physical test.

### Test pair and expected saving

| Image name / card file | Delay pad | Role |
|---|---:|---|
| `BUS DMA8K` / `BUS DMA8K.RMX` | 8,192 NOPs | Optimized comparison and rollback image |
| `BUS DMA4K` / `BUS DMA4K.RMX` | 4,096 NOPs | Experimental half-wait image |

Both use `test/send-return-poc`, four grains and BUILD `D1`. They contain the
same selected modules, post-fader sends and independent T8 returns. Their
internal BRAIN image names differ so the operator can identify the running
variant. They are focused bus test images, not replacements for the separate
RADBUSS7 synth/MIDI package.

The expected instruction reduction is **4,096 NOPs per delay process call
that reaches the pad**, or **256 instructions per stereo sample frame** for
one normal 16-sample call. A split block can reach the pad twice; the experiment
retains the original per-call placement rather than making a new once-per-frame
rule. Measure those split cases separately. The same savings must not be
subtracted from the reverb core, and instruction counts are not physical CPU
percentages. The safe recoverable hardware budget is still unknown.

The production source remains unchanged and the package contains both variants.
No pad-free image is included. Software comparisons can establish equal samples
and state in the emulator, but its DMA timing does not establish that the
shorter wait is safe on a unit. A clean short listening session is also
insufficient: the historical failures were intermittent.

### Package evidence

Build the labelled pair into a fresh output directory:

```sh
python3 tools/hw/build_dma_wait_test.py --out out/dma-wait-20261031
```

The builder fixes the remix, BUILD tag and grain count for this first experiment
and writes both `.RMX` files under `package/BRAIN/REMIXES/`. It must not overwrite
an earlier output directory. Qualify the resulting images themselves, rather
than whatever a later command leaves in `out/mainos_bus.bin`. For example:

```sh
dma8_image='out/dma-wait-20261031/package/BRAIN/REMIXES/BUS DMA8K.RMX'
dma4_image='out/dma-wait-20261031/package/BRAIN/REMIXES/BUS DMA4K.RMX'
python3 tools/verify/verify_bus_dsp_identity.py "$dma8_image" "$dma4_image" --remix test/send-return-poc --engine all --out out/dma-wait-20261031/identity
python3 tools/verify/verify_bus_fastpaths.py "$dma8_image" "$dma4_image" --post-fader --out out/dma-wait-20261031/fastpaths
python3 tools/verify/verify_bus_dsp_state.py "$dma8_image" "$dma4_image" --remix test/send-return-poc --engine delay --exact-state --out out/dma-wait-20261031/state
```

The matched-name binary gate proves exactly one DSP word changes, at shared
P:`0x35e7d`: the immediate in `move #>8192,x0 / do x0,... / nop` becomes
4096. The source snapshot differs only in that literal. The matched-name images
differ in 157 bytes: 149 compressed-upload bytes and eight checksum bytes.
The decoded payload changes only one byte; all
other image bytes outside the verified container and its two checksums match.
This also compensates for the existing `DLSRC` hatch relaxing the build's
signed-multiply census and Y-base source check. The ordinary baseline still
passes those checks. A separate label proof permits exactly two ColdFire
name-string replacements and their container checksums, with both DSP uploads
unchanged. An independent repeat of all three builds reproduces identical images.

The final labelled `.RMX` pair passes all **43 audio comparisons**, **38
additional complete audio/state comparisons**, and the **16,384-block
adversarial delay run** with `--exact-state`. That flag permits no scratch-state
exceptions: all 132 instance words per block, all four raw24 streams and all
262,144 final Y words match. The exact-state mode does not require the original
engine's duplicated L/R control cache, which the preceding optimization removed;
it still checks evolving grain records and saturation of both delay lines.
Thirty focused unit tests pass, including fault injections into the pad,
unrelated firmware bytes, compressed checksums, package names and source anchor.
Documentation validation reports 88 modules, 113 remixes and no problems.
The final 4K image also passes ten full-firmware routing/tail fixtures, four
sounding-host startup fixtures, 6,144 installed/synthetic POST FADER hook cases
and 212 exact RETURNS cases. The tail comparisons cover 803 non-silent frames
per mute fixture, approximately 0.29 seconds; they do not replace long hardware
captures. All four gate processes exit successfully. Generated fixture cards
were removed by the artifact-retention wrapper after success.

An independent meter audit checks every one of **572,928 paired measured
blocks** across the 81 cases, rather than only rounded averages. Core A matches
on every row. Core B saves exactly 4,096 instructions for a whole block or
8,192 for a split block (62 whole-block and 19 split cases). Blocks 0–511 are
excluded only from performance statistics; the audio/state checks include
startup. In this integrated delay-plus-SEND layout:

| Mode | 8K instructions/stereo frame | 4K | Reduction |
|---|---:|---:|---:|
| CLEAN | 759.1875 | 503.1875 | 33.72% |
| Dense four-grain GRAIN | 1215.1875 | 959.1875 | 21.07% |
| REVERSE | 839.1875 | 583.1875 | 30.51% |

The highest observed block falls from 28,753 to 20,561 instructions in the
split-grain cases. These are emulator work counts for these fixtures, not
physical cycle measurements or proof of a hardware deadline. The separate
adversarial state run does not record an instruction meter.

Each `.RMX` is 1,275,323 bytes. SHA-256:

- `BUS DMA8K.RMX`: `de04bf6d4199e41493cd493ac5dc0f6b71b712753b39249372ad519cae07db8c`
- `BUS DMA4K.RMX`: `bcf5044413f3fa068bea1807ff94ce576c3b7b8eba1f673e2e9b8d2357d2df0b`

Receipts are under `out/dma-wait-20261031/` and the independently repeated build
under `out/dma-wait-20261031-rebuild/`. The local package includes the source
commit, build/source/tool hashes, selected modules, exact-image validation,
instruction measurements and checksums. The independently audited
`measurement.json` SHA-256 is
`e9ab081a2342e6c8f011f571c218d8f4c4b71e8bdf3edfc1b1156e7844f38c9c`.
Keep `.RMX` files and captured audio out of Git: they contain proprietary
firmware or local test material. No card copy or flash is performed.

### Paired hardware test

Use a disposable copy of the same project for both images. Confirm the running
name in BRAIN before every take; the boot-screen OS version belongs to the
flashed image and does not identify a switched image. Keep source samples,
tempo, effect settings, routing, capture format and recording/polling workload
the same for each pair.

1. Capture **at least ten minutes per image per workload**, starting with
   `BUS DMA8K`. Reproduce the historical repeated-transient case with T1 BAL
   hard left and an audible sample on the delay host. Retain a quiet right
   channel in the isolated case so full-scale wrong-channel bursts are obvious;
   test the normal wet bus routing separately. Include transport starts/stops,
   parameter edits and a sounding T5 host.
2. Repeat CLEAN, REVERSE and GRAIN with light FX1 work and with the heavier
   FX1 configurations used in the actual project. Include trig/microtiming cases
   that exercise split calls, dense and sparse grains, and changes in controls.
   Record the exact project state; an emulator's synthetic split schedule does
   not prove which split positions a physical take exercised.
3. Exercise T1/T5 host mutes and another source track's mute/LEVEL while tails
   sound. Check that existing tails continue and other tracks' send levels stay
   unchanged. These routing properties remain required in both images.
4. Record the same-duration load trace and audio for each image. Compare core B
   busy/period and T1 FX2 cost, as well as peaks, stalled counters, bad meter
   records, discontinuities and audible corruption. Preserve the complete
   traces instead of only the displayed percentage. Re-test the 8K image after
   a suspected failure to separate the wait change from a shared problem.

[LOAD METER](../../modules/load-meter/README.md) is available in
BRAIN > PERFORMANCE, with LOAD and PROCS tabs. Its USB helper records a series:

```sh
python3 tools/hw/load_meter.py --for 600 --json dma8k-load.json
# After switching to the paired image and restoring the same project state:
python3 tools/hw/load_meter.py --for 600 --json dma4k-load.json
```

The helper labels T1 FX2 as `B1.FX2`; core B carries tracks 1–4. These are
readings of the unit's timers, not emulator instruction counts. Take a fresh
meter baseline for each run because peak and slot counters can retain earlier
work. The [hardware testing guide](HARDWARE_TESTING.md) describes the capture
and meter setup.

For the repeating-transient recording, the existing
[`burst_census.py`](../../tools/harness/burst_census.py) also compares the other
channel against an aligned earlier copy, exposing a quieter block offset beside
a full-scale burst. It assumes **signed 32-bit PCM WAV** and zero-based channel
indices; it must not be fed packed 24-bit or floating-point WAV data. For a
stereo main L/R take use explicit channels 0 and 1:

```sh
.venv/bin/python3 tools/harness/burst_census.py dma8k-main.wav 0 1
.venv/bin/python3 tools/harness/burst_census.py dma4k-main.wav 0 1
```

Its default channels 2 and 3 belong to the historical multichannel recorder.
The detector expects repeating audio and flags large one-off discontinuities;
zero detections do not establish general audio correctness or a timing margin.
The [failure register](FAILURE_MODES.md) records both the original read-back
race and later burst investigations. Any new wrong-channel burst, click,
unexpected silence or stalled DSP counter blocks acceptance of the 4K variant.

### Switch back without reverting the optimizations

Load the pair through MAIN MENU > BRAIN > REMIXES using the same existing
REMIX SWITCH workflow. Select **BUS DMA8K** to restore the original wait while
keeping the optimized DSP and post-fader/return behavior. Select the image under
**FLASHED** to return permanently to the flashed OS and clear the saved remix
selection.

REMIX SWITCH can remember its selection in `BRAIN/card.work`; a power cycle
alone may reload the experimental image. To bypass a saved selection for one
boot, hold FUNC at power-on and choose EXIT in the stock STARTUP MENU. Booting
with the card removed also leaves the flashed image running. These steps follow
the current [REMIX SWITCH instructions](../../modules/remix-switch/README.md);
the saved-selection behavior depends on the switcher in the flashed image too.
Do not claim the fallback was exercised on hardware until it has been.
