# MIDI SRAM

Provides 16,384 bytes of retained storage for MIDI modules. Select **MIDI SRAM**
with **MIDI Part State**. It adds no panel controls and does not alter audio-step fields.

The pool uses protected bytes in the current bank's MIDI step records in SRAM.
Those bytes are excluded from native bank files and clipboards. Clients own
their allocation, checksum and checkpoint publication; this is not a project
file format or a replacement for saving.

Harmony's **MIDI TRACK** layout uses the full pool for its 8,192 steps and
track metadata. PLOCKS and MIDI Scenes retain their own separate allocations.
A reset that clears SRAM invalidates retained state; clients recover from
their validated project companions.

[Allocation contract, implementation and verification](DEVELOPMENT.md).
