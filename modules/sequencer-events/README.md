# SEQUENCER EVENTS

Platform owner of native transport start/resume and accepted MIDI-output hooks.
Select it through the dependencies of its clients. It adds no controls, storage,
or musical transformations. Each selected client is notified once per boundary.

Register `(module key, symbol prefix, events)` in `CLIENTS` in `manifest.py`,
following STORE. Missing clients are omitted at build time. Missing symbols fail
linking. Callback order is registration order; it must not encode dependencies
between clients' musical state. Clients must not emit MIDI or re-enter these hooks.

| Event | Callback arguments | Timing |
| --- | --- | --- |
| start | d0: native PLAYING value | After the native PLAYING write |
| resume | d0: native PLAYING value | After the native PLAYING write |
| midi_sent | d0: MIDI track 0–7; d1: native pool kind; d2: velocity; d3: pitch | Native output acceptance / ownership replacement |

Callbacks return normally and may clobber d0–d7/a0–a6. Preserve SP and the
interrupt mask. The dispatcher restores native registers and condition codes;
continuations execute displaced instructions once. State is stack-local.

The MIDI event includes zero-velocity output and live arp pools. Clients decide
which outputs affect their musical state. Rejected output never reaches these
native boundaries. Acceptance does not prove UART delivery or device playback.
HARM and Follow ignore zero velocity and live arp for accumulator/register updates.
EUCLID resets its own clock with its own interrupt guard.

This is a synchronous boundary API, not a generic message bus, note-transform
pipeline, transport controller, or replacement for STORE. STOP and MIDI input
are not inferred from these sites. Add a new event only with an audited native
boundary, argument contract, ordering, and installed-hook behavior tests.
