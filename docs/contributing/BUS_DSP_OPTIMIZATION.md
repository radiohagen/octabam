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
sources are unchanged between that revision and `f8141428`. The reviewed
branch is based on `f8141428`; neither a moving remote branch nor an earlier
PR build is the behavioral oracle.

For publication to the `radiohagen/octabam` fork, upstream
`92a63bacc51ebf4c5c80a930670a9c7e973e150e` was merged on 27 October 2026.
Its two additional commits change only `FAILURE_MODES.md` and `DEMAND_LOAD.md`;
firmware sources, build inputs and verification tools are unchanged. The merge
preserves the measured commits and the reproducible source references below.
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

Use the reviewed branch's tools, the user's own OS 1.40C, the pinned source
revisions above, and identical build options. Keep every image under a distinct
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
The sounding-host receipt is `out/postfaderhosts/results.json`; the earlier
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
| Final integrated four-grain image | `9317770bbf847a94f47508cb087681c0822517d3730868cc87c0f047d59633e8` |
| Superseded integration image; startup negative control | `7b7c545cd11e426bef893743095b989c59d320ace51fa1eb4b999ca1b4134d4a` |
| Measured DSP host | `e936529aadccbc623018f191eff8d30aab08e32be73f52c2c75d834a7b216e8f` |

## 6. Acceptance still required

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
