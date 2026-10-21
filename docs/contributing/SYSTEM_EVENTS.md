# Shared native events

Two platform modules own recurring native hook collisions. They follow STORE's
explicit build-time client tables and do not change project formats or memory
reservations. They are required by the corresponding clients, including when a
client runs alone: there is one production path to validate.

| Owner | Boundary | Composition rule |
| --- | --- | --- |
| SEQUENCER EVENTS | Native PLAY/resume publication and accepted MIDI output | Every registered client receives one notification |
| EDIT EVENTS | Held-step encoder entry and native pattern/track data movement | First matching read-only editor predicate; every copy subscriber |
| STORE | Project/Part persistence | Existing STORE contracts, including failure guards |

These boundaries follow native operations, not feature names. HARM, Follow,
EUCLID and PLOCKS are clients. A new machine can register an editing context
without changing the dispatcher. A new clock consumer subscribes without a
HARM/Follow/EUCLID-specific branch. No platform module knows chord formats,
register policies, effect controls or retained storage layouts.

The contracts are in [SEQUENCER EVENTS](../../modules/sequencer-events/README.md)
and [EDIT EVENTS](../../modules/edit-events/README.md). Do not use a universal
callback interface: consumption, notification and pre/post data maintenance have
different semantics. Start and resume remain distinct events even though today's
clients reset on both. MIDI acceptance is distinct from audible or UART output;
live pool and velocity filtering belong to the clients.

The editing module covers the shared copy sites used for clipboard and undo,
not all similarly named operations. Native audio and MIDI trig-clear/paste paths
currently have distinct owners and stay there. Moving them without a shared
boundary would enlarge the public ABI without resolving a collision. Add such
an event when needed, with its actual stack/register arguments, ordering and
failure behavior verified. A hook ledger is necessary but cannot prove that a
copy updates every side table or an edit reaches the intended control.

## Migration and verification

Select SEQUENCER EVENTS for MIDI Follow and EUCLID. Select EDIT EVENTS for
PLOCKS P2. HARM requires both. Remove HARMONY FOLLOW and HARMONY PLOCKS selections.
HARM and Follow retain their root/voice agreement in their own implementation.
No bridge may continue owning any platform detour.

`verify_system_events.py` independently assembles production dispatchers with
zero, one and three unrelated clients. It exercises both transport/output paths,
context fallthrough and explicit precedence, callback register clobbers, original
arguments, stack balance and exactly one native copy. `verify_event_clients.py`
checks the selected image's registered symbols and installed detours. Real
Harmony/PLOCKS copy/undo, accumulator and Follow gates, EUCLID engine traces and
project-backed panel journeys are required in addition to these platform tests.

The `shared-events` selection exercises all current consumers together without
bridges. Standalone consumer selections exercise omission of unrelated clients.
System-module tests do not establish physical battery retention or device timing.
