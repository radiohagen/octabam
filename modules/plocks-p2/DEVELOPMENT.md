# PLOCKS-P2 contribution notes

The page-2 editor marks a held trig as edited and clears native pending tap
masks before committing a lock. This lets release distinguish an edit from
a bare tap, preserving the lock just entered. `verify_plocksp2.py`
checks the held-step edit followed by release and subsequent bare-tap clearing.

### Stock Address Provenance

These are stock **1.40C** addresses, checked in the local MAIN_OS disassembly.
The native knob-commit routine starts at `0x4004ecfc`: at `0x4004f0aa`
it writes 1 to the 32-bit word `0x460d173a`, then clears the six 16-bit
words below. `pe_commit` mirrors that sequence.

| RAM word | Native knob-commit clear | Native trig-down read | Native release read / clear |
|---|---|---|---|
| `0x460d1a9e` | `0x4004f0b2` | `0x40050fee` | `0x4005fbe2` / `0x40060a5a` |
| `0x460d1aa0` | `0x4004f0b8` | `0x40050ff4` | `0x4006001a` / `0x40060a68` |
| `0x460d1aa2` | `0x4004f0be` | `0x40050ffa` | `0x4005feaa` / `0x40060a76` |
| `0x460d1aa4` | `0x4004f0c4` | `0x400516a6` | `0x40060674` / `0x40060a84` |
| `0x460d1aa6` | `0x4004f0ca` | `0x400516b8` | `0x40060a14` / `0x40060a92` |
| `0x460d10dc` | `0x4004f0d0` | `0x4003004a` | `0x4003013a` / `0x40030144` |

The main trig-down routine starts at `0x40050f20`; the release routine at
`0x4005fb44`. Release also reads the edited word at `0x40060b04` and clears
it at `0x40060b14` when the held-trig mask at `0x460d174a` is zero.
The sixth mask belongs to an alternate trig path starting at `0x4002fff8`,
called by release at `0x40060aa8`. Its consumed bits are cleared separately.
The common reset helper at `0x400339b0` clears all six masks as well.

The addresses, widths and matching stores are statically observed. The names
“edited” and “pending tap masks” describe their inferred role from those
read/write paths, corroborated by the release regression. They are not
firmware symbols. This is not an exhaustive claim about every reader.

Under the emulator, a recorded page-two lock survives release; a subsequent
bare tap clears it. Project/card persistence and protected-file refusal are
also covered by the passing regression. These are emulator measurements;
physical button timing is not verified on the unit for this build.
