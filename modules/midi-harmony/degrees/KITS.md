# Native Part and KITS integration

Harmony and Follow use native Part settings. KITS needs no source changes.

## Project scope and stock firmware

KITS keeps a separate library of up to 255 kits in each project's `kits.work`
and `kits.strd`. Kit numbers are local to that project. A kit contains the
whole Part, including Harmony and Follow's MIDI setup fields; it does not
contain the project's sample files or pattern degree/chord locks.

Stock 1.40C uses native Parts and has no KITS recall behavior. Its Part loader
can normalize extension fields, so a working Part saved on stock and a saved
kit record can disagree. Keeping the kit files is not a guarantee that edits
made on stock will survive later kit recall. Keep a separate project copy for
stock use. The tests below qualify KITS with the modules enabled; they do not
establish a lossless round trip through arbitrary stock edits.

## Current native storage and ABI

Each MIDI track has a native 36-byte SETUP record at Part offset `0x4e2`.

| Offset | Contents |
| --- | --- |
| 3 | Follow source |
| 5 | HARM OFF/NOTE/CHORD |
| 12 | Follow mode/response, bits 0/1 only |
| 13 | Remembered fixed octave |
| 15 | Remembered relative octave |
| 16 | Packed VOIC/SPRD/ROOT |
| 17 | Native KEY, read through the shared snapshot |
| 18 | Base CHRD bits 0..2; SIZE NAT/2/3/4 bits 3..4; valid byte 0..31 |
| 19 | Base DEG, 0..83; default 35 |

Context is `bank*4+workingPart`, 0..63. Public shared entries preserve all
registers except d0/CCR. `mp_ui_context` identifies the selected Part;
`mp_play_context(d0=track)` identifies the per-track engine context, with
applied-engine fallback, never UI fallback. `mp_read`, `mp_write`,
`mp_read_key` and `mp_epoch` use explicit contexts. Getters distinguish UI,
playback and captured-event contexts deliberately.

MIDI PART STATE owns boot-safe ROM gates for native memcpy/init. During an
ordinary native working-Part replacement it publishes `mp_snapshot_bank`,
`mp_snapshot_parts` and the outgoing SETUP snapshot, then calls
`hd_part_before(d0=aligned Part address)` once per affected Part. DEG detaches
outgoing root/queued provenance and suppresses reattachment while the snapshot
is active, including Follow dependencies. Native bulk copying remains
interruptible. A short final publication updates epochs and releases the
snapshot. Unrelated Parts stay attached. The superseded degree-only copy
wrapper and its unused verifier have been removed.

Pattern roots are 131-byte records: 64 degrees, 64 native edit snapshots,
representation, outgoing scale and last context. One runtime bank is 16,768 bytes. Packed storage reconstructs the canonical
NOTE snapshots and omits context: CHRD plus roots is 10,368 bytes, or 10,400
with its header. Files use HDP3/version 3; retention uses HDN3/version 3.
Empty files use HDP0. See the [storage invariant](DEVELOPMENT.md#compact-hdp3--hdn3-storage).
Companions contain no Part defaults and ignore Part assignments/defaults in
their native fingerprint. Loads detach reusable physical-slot provenance.
Strict validation, failed-write protection and atomic publication remain.

## Verification

`verify_harmony_degree_kits_port.py --scenes --project DIR` checks 18
resident/nonresident mode transitions, incoming defaults, explicit locks,
held-note releases and unchanged Kit library data. Run the native KITS gate
as well. These checks use disposable virtual cards, not physical hardware.
