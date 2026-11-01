# POST FADER

Bus sends follow track LEVEL, scene XLEV (XLV), mute and solo without changing another
track's send gain. This optional module adapts sanderlegit's
[PR 542](https://github.com/sambanks/octabam/pull/542) and the local
`codex/modules/post-fader` prototype to the current module registry.
It is selected by `test/send-return-poc`; hardware acceptance is pending.

After the stock record builder runs, the ColdFire hook scales DEL and REV
by `(LEVEL/128)^2`, using the MAIN mixer snapshot after mute and solo.
It changes only the transient DSP record, leaving Part data, parameter
locks, panel values and MIDI feedback unchanged. The hook uses the integer
high byte of mixer snapshot LEVEL. Scene XLEV then attenuates that coefficient using the
stock mixer's sine curve, relative to its unlocked value (`0x7f00`). Thus
unlocked scenes keep the previous send coefficients exactly, and XLEV zero
stops new excitation. The table is extracted from the user's stock image at
build time; no stock table bytes are stored in the repository.

AMP VOL, its envelope and scene XVOL already affect the audio reaching the
effects, so the hook does not multiply those controls a second time. Source
FX1 output also naturally reaches SEND. This remains a frame-rate control
path with the existing send smoothing, not a copy of the stock mixer's
sample-by-sample ramp. The existing MAIN high-byte quantization remains.
CUE gain, output volume and T8 master/return gain are separate destinations;
they do not attenuate source excitation again.

The original nonzero send reserves its normalization share even at LEVEL
zero, scene XLEV zero or while muted. Bit 15 of each transient control halfword carries
that participation marker; it becomes DSP bit 23. The selected DSP source
transform uses the marker for client counts and masks it before gain
arithmetic. This prevents the old `1/sqrt(N)` gain jump when a track is
muted or faded. A send-knob change through zero still changes membership;
this is deliberate. At LEVEL 55, the send factor is approximately 0.185.

The scaled low byte remains fractional precision for SEND and both hosts'
DEL controls, and BusVerb REV. BusDelay REV keeps its held MIDI-note byte,
so that one send retains its original seven-bit coefficient precision.
A note alone never reserves a REV share. Engine IDs come from the selected
remix's bound registry; unselected stock effects and RETURNS are untouched.
Id 0 is treated as SEND only when that is the remix's fallback.

Muting stops excitation through the existing send smoothing and bus
latency, without clearing effect state. Shared tails cannot identify which
track originally made them. Independent T8 RETURNS is needed to prevent a
T1/T5 host mute from cutting its shared audible return. The test remix
selects both modules and uses T8 as master for the audio gate. There is no
new persistent setting or project format; omitting POST FADER leaves the
upstream send transport and normalization behavior unchanged.

## Verification

`tools/verify/verify_postfader_hook.py test/send-return-poc` executes the
installed detour with the stock builder stubbed. It checks both record
banks, every LEVEL and XLV index, scene endpoints, zero and fractional controls,
held notes, stale marker bits, selected IDs, non-send records, mixer data and
saved registers. It also verifies every installed curve coefficient against
the stock table. There are 4,336 installed-image and 8,672 synthetic-ID cases.
With `--baseline-ref 8e930625`, it measures additional ColdFire instructions
against the original hook on identical inputs. An exhaustive curve check
bounds the difference from the exact normalized stock ratio to one transient
control LSB across 8,225,790 possible pairs.
It also assembles the hook in private scratch with IDs 33/34/35 and with
SEND alone at 39, checking remapping and absent-engine guards. Those
synthetic cases prove the ColdFire ID contract, not full 64-ID firmware.

`tools/verify/verify_postfader_dsp.py test/send-return-poc --image IMAGE`
reads the DSP uploads from that image's boot pointers, including packed
window code. Tagged and untagged REV words with held notes 0, 72, 84 and 96
must produce the same delay audio at all 24 bits and the expected note and
pitch state. With no held note, PTCH sets the pitch; a held note overrides
it. Repeat with a separately built two-grain image and `--grains 2`.

`tools/verify/verify_postfader.py test/send-return-poc --image IMAGE
--project TEMPLATE` copies a local project into owned scratch and builds a
deterministic tone/burst fixture with the existing `usb_sig_project.py`.
It runs the real builder and DSPs. A silent T7 retains send 100 while its
mute, LEVEL or solo exclusion changes; the other sender's return must be
bit-identical. Changing original membership to zero is a positive control
that must change the return. Dynamic MIDI mutes of T1, T2 and T5 after a
200 ms T2 burst must preserve the non-silent tail exactly. The gate also
checks the mixer snapshot to prove each mute actually arrived.
A continuous tone on a muted source must produce no return, proving that
muting also stops new excitation through the actual DSP decoder.

`tools/verify/verify_postfader_hosts.py test/send-return-poc --image IMAGE
--project TEMPLATE` adds four sounding-host cases: T1 and T5, each audible
and already muted in the saved project. The tone starts on the first trig.
Both muted hosts must retain nonzero dry DSP audio and original send
participation while their send coefficients, wet buffers and master output
remain zero after warm-up. Each audible counterpart must excite both buses.
This catches an early unscaled initialization packet seeding BusVerb's DEL
ramp during warm-up; the selected POST FADER path now defers that ramp seed
until the first active sample. Running tails keep their existing state.
The gate records image, emulator, script, fixture and output hashes in
`out/postfaderhosts/results.json`. It is registered as an image gate, uses
`out/mainos_bus.bin` by default, accepts `OT_PROJECT` instead of `--project`,
and skips when no local template is configured or the port binary is unavailable.

`tools/verify/verify_postfader_volume.py test/send-return-poc --image IMAGE
--project TEMPLATE` adds eight full-firmware source-volume cases. It explicitly
unmutes both scenes in its owned saved project, installs known live scene
endpoint rows, then uses the actual crossfader CC/morph/publisher path.
Snapshot readback must confirm XLEV zero. A delayed-onset tone then produces
no new wet audio, while existing tails and the other sender remain bit-identical
across 803 compared frames. AMP VOL 64/127 attenuates dry and both isolated wet
buffers by approximately 0.254; AMP VOL zero and scene XVOL zero silence the
incoming audio without scaling send controls again. An old frozen image with
`--cases audible,xlev_zero` must fail the new-excitation assertions. This checks
live scene behavior, not saved scene-lock parsing or physical crossfader timing.

These checks do not establish physical DMA timing, long-tail stability,
cue-only use, or an instantaneous excitation cutoff.
The integrated fixture uses MUTE MODES' stock OT setting; alternative
trigger-only and dry-cut modes have their own semantics and need separate
qualification.
No card or user project is edited. Historical October 13 prototype gate
results are not evidence for this revised transient transport.

The [bus optimization review](../../docs/contributing/BUS_DSP_OPTIMIZATION.md)
records the original authorship, exact changes, measurement method, regression
evidence and remaining acceptance requirements.
