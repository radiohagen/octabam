# Protected MIDI retained pool

Opt-in support module for compositions that need additional retained capacity.
Select `MIDI SRAM` with `MIDI PART STATE`. It adds no panel control and provides
16,384 retained bytes in fields 30/31 of each native MIDI step record in the
current-bank CS1 mirror: 16 patterns × 8 tracks × 64 steps × 2 bytes.
Audio step fields are untouched: audio field 31 is a sample lock.

The pool exists only in SRAM. The MIDI PART STATE native-copy boundary skips
these destinations and returns `0xff` for these source bytes, so pool data
never enters native DRAM, clipboards or bank files. Eight MIDI-only direct
write loops stop at the 30 parameter fields. All other native bytes retain
the stock copy/clear behavior. The cold ROM boundary remains stock until the
platform loader has activated the runtime. A whole-CS1 reset invalidates the
client headers; an ordinary bank copy must preserve the pool.

`rp_read` and `rp_write` check offset and length before every transfer. They
do not publish a checkpoint: the client owns its dedicated header, checksum,
writer serialization and final atomic magic store. The experimental Harmony `MIDI TRACK` layout addresses each step directly
and owns all 16,384 bytes, including its track metadata. It does not use
`rp_read`/`rp_write` as a cross-track allocator. PLOCKS is not a client in
that selection. Clients must not bypass
this allocation or assume that native padding in DRAM is retained storage.

Each two-byte range is declared individually in the resource ledger. Do not
replace these claims with an assertion that the intervening stock data is
unused. New stock/module writers into the pool invalidate this design and
must be added to its protection and verification before composition.

Validation commands, after `make bus REMIX=midi-sram`:

```
.venv/bin/python tools/verify/verify_midi_sram.py
.venv/bin/python tools/verify/verify_midi_sram_port.py --project <fixture-project>
```

The linked gate checks bounded I/O, native copies and track clears with an
observer that rejects every pool write. The port gate compares native data
against stock across complete operations and retained restarts. On this branch,
the combined capacity gate is `tools/verify/verify_harmony_track_port.py`, run
against `harmony-track-bus`: 8,192 Harmony steps and 4,768 upstream PLOCKS locks.
The older `verify_integrated_retention_port.py` targets the previous compressed
PLOCKS layout and is not applicable to this experiment. Receipts are under `out/`. No physical
battery retention, firmware installation or hardware timing is established.

## Source and acceptance

Edit `pool.c`, then run `python3 modules/midi-sram/generate.py` and the same
command with `--check`. Callers must handle a rejected bounds check; a failed
transfer must never publish a valid client header. Hardware cold starts,
long power-offs and interrupted checkpoints remain acceptance work. A port
restart models retained bytes; it does not prove battery or reset behavior.

The full-firmware commands above share Harmony test helpers and are available
in the complete integration stack. The standalone branch includes its own
linked-code gates through `make check`; it has no runtime dependency on Harmony.

For Harmony track-local retention, the installed clear paths intentionally
update these fields with the correctly cleared Harmony state. The generic
pool gate isolates the underlying native clear, while
`verify_harmony_track_retention.py` checks installed Harmony clear/restore
behavior and `verify_harmony_track_port.py` runs full-firmware restarts.
