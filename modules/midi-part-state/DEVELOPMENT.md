# MIDI Part state

Shared support for MIDI Follow, MIDI Harmony and MIDI Loopback. Include `MIDI PART STATE`
with these modules; the repository's remix selections already do so. It adds
no panel control and does not require KITS. One owner supplies the
native hooks whether Follow, Harmony or both are selected.

Working native Parts are the authority. UI access uses the selected working
Part; engine access uses the playing context of each MIDI track. Custom writes
update native working bytes, the current-bank CS1 mirror and native dirty bits.
Native Save/Reload and KITS carry these bytes through their existing storage.
There is no legacy decoder, migration store or persistent shadow copy.

Small ROM entry gates preserve stock behavior before the platform runtime is
loaded. The native call immediately after the verified loader enables their
DRAM targets, preserving the stock callee's original return address.

While native memcpy or Part initialization replaces a resident bank's working
Parts, readers see a complete outgoing snapshot of all four MIDI SETUP arrays
(1,152 bytes). The single native UI writer publishes the incoming settings by
clearing the active snapshot pointer after the operation. Snapshot preparation
and the native operation leave interrupts enabled. Final epoch/settings publication
uses a short interrupt mask, with no native copying or callbacks inside it. Native copy arguments,
register returns and interrupt level are preserved; condition codes are not
part of the C calling contract. Nested stock operations retain the outer
snapshot. Bulk operations crossing bank boundaries are outside this live Part
boundary and require stopped-project lifecycle validation.

`mp_read` and `mp_read_key` use the snapshot. Direct native memory readers do
not; new MIDI consumers must use the explicit-context API. Runtime held-note
ownership is separate and must keep the original release identity. Each replaced Part advances a runtime-only epoch. Follow uses that epoch to
wait for the new Part's next ordinary trig before LIVE response can act;
Harmony uses it to discard the outgoing Part's AUTO history. Existing note
release ownership and deadlines remain unchanged. Ordinary setting edits do
not advance the epoch.

DEG receives one `hd_part_before` callback per affected Part after snapshot
publication and must consult the affected-Part mask to defer reattachment.
The degree integration gate covers that combined path, including interrupted
replacement with all eight tracks and four pending-event slots per track.

The linked-code gates exercise explicit contexts, bounded writes, native
copy/initialization byte and ABI equivalence, and interruption while settings
are partially replaced. Full firmware checks below cover native Part and
project persistence separately. Neither layer establishes hardware acceptance.

SETUP offset 12 is a shared flags byte: bit 0 reserved, bit 1 Follow
TRIG/LIVE response, bits 2–3 Loopback DEST (EXT/INT/BOTH; 3 reads as EXT).
This module owns the native range (0..15) and byte claim. Each writer preserves
the other settings. Fresh Parts initialize all flags to zero. Follow's REG
now occupies its own packed field at offset 15, not the shared flag byte.

This module also owns the shared transport start/resume and successful MIDI
note-on continuations. It dispatches only selected consumers: Follow resets
or commits its register history, and Harmony resets or advances ACC. These
hooks preserve native registers/replay; absent consumers compile out. This
keeps standalone Follow, standalone Harmony and their combination on the
same event boundaries without overlapping hook claims.

For full firmware checks on a copied project, run
`tools/verify/verify_midi_part_port.py --project DIR` for native Part
Save/Reload/Clear/Paste, and
`tools/verify/verify_midi_harmony_port.py --project DIR --settings-only`
for actual panel edits, project SAVE, disk reload and retained-memory resume.
The latter requires Harmony and also checks Follow fields when present.
The low-level native Clear initializes both working and saved Part; unlike
Reload/Paste, its CS1 working mirror refresh belongs to its caller.

NOTE SETUP YES refreshes RFOL/HARM staging from the selected Part before
stock confirms all six fields. This preserves immediately applied module
edits without replaying mode conversion or changing stock staged controls.

## Composition and acceptance

The standalone `midi-part-state` remix exercises the boundary without a player
module. Follow and Harmony select it explicitly; KITS and MIDI SCENES remain
optional clients of native operations. Their implementations are unchanged.
Run `make check REMIX=midi-part-state`, then the caller's own image gates when
composing. Linked interleaving probes establish coherent publication under the
modeled interrupts; they do not reproduce caches or electrical startup timing.

The full-firmware commands above share Harmony test helpers and are available
in the complete integration stack. The standalone branch includes its own
linked-code gates through `make check`; it has no runtime dependency on Harmony.
