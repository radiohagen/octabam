POST FADER makes the delay and reverb sends follow the source track's
LEVEL, scene XLEV, mute and solo. It is an optional module in the
`test/send-return-poc` remix, together with [RETURNS](returns.md).
Hardware acceptance is pending.

## Source volume and scenes

DEL and REV follow the mixer's LEVEL and scene XLEV snapshots. Moving a
source to XLEV zero stops new delay/reverb input through the normal send
smoothing. Existing repeats and reverb continue to decay. Unlocked scenes
preserve the previous send gain.

AMP VOL, its envelope and scene XVOL already affect the audio reaching
the effects. Their changes therefore affect new bus input as well; POST
FADER does not apply those gains a second time. CUE gain and output volume
remain destination controls and do not change the source sends.

Muting or fading one track keeps the other tracks' send levels unchanged.
The source retains its original send's normalization share even when
LEVEL or XLEV reaches zero. Changing a DEL or REV knob through zero still
changes participation. A host saved muted also starts with zero wet
excitation, including during engine warm-up.

## Keep the returns audible

Use POST FADER with [RETURNS](returns.md) to move both shared returns to
T8. This allows a T1 or T5 mute to stop that host's new bus input while
other tracks and existing tails remain audible. A master mute still
affects the complete mix.

The module changes transient send controls; saved Part values, parameter
locks, panel values and MIDI feedback stay unchanged. It uses frame-rate
snapshots with the existing send smoothing and bus latency, so it does
not provide an instantaneous cutoff or reproduce the stock mixer's
sample-by-sample ramp. The current checks use MUTE MODES' stock OT setting;
the alternative trigger-only and dry-cut modes need separate qualification.

Local checks cover scene endpoints, source AMP/XVOL attenuation, muted
hosts, preserved tails and unchanged contributions from other tracks.
They do not establish physical DMA timing or hardware performance.
