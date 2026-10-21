# EDIT EVENTS

Platform owner of held-step encoder dispatch and the native pattern/track copy
sites shared by extended editors. It adds no controls or retained storage.

Register `(module key, symbol prefix, events)` in `CLIENTS` in `manifest.py`,
following STORE. Only selected clients enter the generated tables; unresolved
handlers fail linking. Declare `requires=('EDIT EVENTS',)` and select the module.

| Event | Contract |
| --- | --- |
| held | `<prefix>_claim(d0=encoder, d1=delta)` returns zero to pass; nonzero selects `<prefix>_handle` with the original native entry frame |
| copy_pre | d0=destination, d1=source, d2=length; before native data moves |
| copy_post | same original arguments; after native data moves |

Held predicates must be read-only. Registration order is explicit precedence:
the first matching predicate wins. A new editor must declare its exact context
and test overlap and fallthrough with existing editors. Handlers return as the
native held editor would; they must not re-enter this dispatch. No owner means
one native fallback. This supports multiple editors on the same track type.

Copy notifications visit every client in registration order. Each client owns
its side data and filters addresses/lengths for its supported objects. Native
memcpy executes once between phases, and its result is returned unchanged.
Callbacks may clobber d0–d7/a0–a6; preserve SP and interrupt mask. Dispatcher
frames are stack-local. Client scratch state may impose stronger non-reentrancy.

The copy sites include pattern/track clipboard and undo transfers. This does
not pretend every clear/paste command is memcpy: distinct MIDI/audio trig-clear
and trig-paste hooks remain in their owning modules. Project/Part persistence
belongs to STORE. Add further shared editing boundaries here only after auditing
the native ABI and before/after semantics, with behavior tests at installed hooks.

HARM's pre/post clients preserve degree, chord and accumulator side data.
PLOCKS P2's pre client preserves FX page-two locks. Neither callback calls the
other or calls native memcpy. Their held predicates distinguish Harmony controls
from audio FX SETUP. The dispatcher has no knowledge of either data format.
