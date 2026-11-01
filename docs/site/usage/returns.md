RETURNS places independent DLY and VRB return controls on T8's FX2. It is
an optional module in the `test/send-return-poc` remix, together with
[POST FADER](post-fader.md). Hardware acceptance is pending.

## Routing

With MASTER TRACK enabled, both returns enter T8 before FX1 and LEVEL.
T8's processing and master level therefore apply to the complete mix.
With MASTER TRACK disabled, the returns enter MAIN directly; T8 still
carries their controls, but its own track processing does not affect them.

T1 and T5 keep [BusDelay](busdelay.md) and [BusVerb](busverb.md) in their
FX2 slots. Their dry track level no longer controls the shared wet
returns, so muting either host leaves the other tracks' returns audible.
The host FX2 slots remain occupied by the engines.

## Sends and tails

[POST FADER](post-fader.md) controls new audio entering the buses. Together,
the two modules let a source's LEVEL, scene XLEV or mute reduce new input
while existing repeats and reverb decay normally. Other tracks' send
levels remain unchanged. Muting the master itself still affects the
complete mix.

In the test remix, RIG HOSTS assigns RETURNS to T8 for new Parts. Existing
projects retain their saved effect assignments; prepare and test a copy
before playing. RETURNS is inactive on other tracks. Live removal is not
claimed seamless, so keep it assigned during a performance.

Local checks cover independent return gains, master routing, host dry
isolation and tail continuity. Hardware timing and complete-frame DSP
load still need acceptance on the unit.
