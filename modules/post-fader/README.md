# POST FADER

Bus sends follow track LEVEL, mute and solo without changing another
track's send gain. This optional module adapts sanderlegit's
[PR 542](https://github.com/sambanks/octabam/pull/542) and the local
`codex/modules/post-fader` prototype to the current module registry.
It is selected by `test/send-return-poc`; hardware acceptance is pending.

After the stock record builder runs, the ColdFire hook scales DEL and REV
by `(LEVEL/128)^2`, using the MAIN mixer snapshot after mute and solo.
It changes only the transient DSP record, leaving Part data, parameter
locks, panel values and MIDI feedback unchanged. Mixer snapshot LEVEL is
an integer high byte. This is the track LEVEL law; separate scene XLV,
CUE routing and stock's split-aware mixer ramp are outside this module.
AMP VOL has already affected the signal reaching the effects.

The original nonzero send reserves its normalization share even at LEVEL
zero or while muted. Bit 15 of each transient control halfword carries
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
banks, every LEVEL, zero and fractional controls, held notes, stale marker
bits, selected IDs, non-send records, mixer data and saved registers.

`tools/verify/verify_postfader.py test/send-return-poc --image IMAGE
--project TEMPLATE` copies a local project into owned scratch and builds a
deterministic tone/burst fixture with the existing `usb_sig_project.py`.
It runs the real builder and DSPs. A silent T7 retains send 100 while its
mute, LEVEL or solo exclusion changes; the other sender's return must be
bit-identical. Changing original membership to zero is a positive control
that must change the return. Dynamic MIDI mutes of T1, T2 and T5 after a
200 ms T2 burst must preserve the non-silent tail exactly. The gate also
checks the mixer snapshot to prove each mute actually arrived.

These checks do not establish physical DMA timing, long-tail stability,
scene XLV behavior, cue-only use, or an instantaneous excitation cutoff.
No card or user project is edited. Historical October 13 prototype gate
results are not evidence for this revised transient transport.
