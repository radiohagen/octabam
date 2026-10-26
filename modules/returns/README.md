# `returns` — RETURNS

T8's FX2 controls independent delay and reverb returns with DLY and VRB.
With MASTER TRACK enabled, the returns enter T8 before FX1 and LEVEL.
With MASTER TRACK disabled, they enter MAIN directly; T8 still carries the
return controls but its own track processing does not affect the returns.

T1 and T5 retain BusDelay and BusVerb in FX2 and can play their own sounds.
Their track LEVEL/mute changes affect those sounds and their post-fader sends;
existing bus tails and other tracks' contributions continue. A master-level
change still controls the whole mix. RETURNS does not free the host FX2 slots.

The separate POST FADER module controls new audio entering the buses. Both
modules are needed to keep muting a host from muting other tracks' tails.
Keep the send auto-gain denominator independent of mute/LEVEL so another
track's send level does not jump when one source is muted.

The effect is inert off T8, including init. On core B init and proc return
immediately. Removing RETURNS restores the servers' original host prints
once their liveness protocol expires. In the locked bus remix, RIG HOSTS
assigns T8 automatically for new parts; existing projects require the host
conversion command, which should be used on a copy.

The implementation follows the return protocol from PR #542, with these
changes for current upstream:

- The shared delay ring is `0x30100..0x301ff`, its stamps `0x30200..0x30207`,
  and liveness at `0x30208`. The old `0x36200` allocation now contains code.
- RETURNS owns the shared allocation on both cores. BusVerb owns private
  Y `0xe00..0xe26`. The selected RETURNS transformer uses this buffer
  for both independent wet and fallback host prints; unselected builds keep
  the original engine source unchanged.
- Init checks the host slot before clearing either shared return gain.
- Ordinary two-word branches work with the current assembler.

The delay reader consumes stamped buffers three rotations behind its writer.
The reverb buffer stays on core 0. Each return gain glides toward
`(knob/128)^2`, a quarter of the gap per block. The mix hook runs even though
proc has no sample loop: its inner work is 12 executed instructions per
stereo sample with MASTER enabled and 17 without, plus setup and smoothing.
Those counts are not hardware cycles or measured utilization.

Live removal is not claimed seamless: the delay producer waits three blocks
for liveness to expire, and the consumer can then drain previously stamped
buffers while the host print resumes. The locked remix keeps RETURNS assigned.

The focused gate checks 212 exact DSP cases, including MAIN/MASTER arithmetic,
all 128 gain targets, every ring rotation, stale/fresh consumption, and init/proc
on the wrong track or core. It also checks the installed module bytes and hook.
This port has no new hardware acceptance. Required
checks include memory ownership and write bounds; exact fallback audio;
independent returns and host dry isolation; LEVEL/mute tail continuity;
wrong-track init; all split positions; return activation/removal; stereo
impulse timing; current cross-core scheduling and complete-frame DSP load.

The [bus optimization review](../../docs/contributing/BUS_DSP_OPTIMIZATION.md)
records the original authorship, exact changes, measurement method, regression
evidence and remaining acceptance requirements.
