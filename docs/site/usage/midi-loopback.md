Route each MIDI track to external MIDI, the Octatrack's internal MIDI receiver,
or both. For example, an internal MIDI track can sequence audio-track CC
controls while another MIDI track drives external equipment.

## How to Use It

1. On a MIDI track, open NOTE SETUP with FUNC + SRC.
2. Choose A: CHAN, then press A to apply it and open ROUTING.
3. Turn A: DEST to EXT (default), INT, or BOTH. Changes apply immediately.
4. Press A, YES or NO to close. Track/page keys close the window first.

CHAN shows an I or B suffix for INT or BOTH. CHAN OFF still disables sequencer
output. Receiver channel assignments and receive switches still apply.
DEST is saved per MIDI track in each native Part. Fresh Parts use EXT.

## Optional note translation

Select MIDI LOOPBACK TRANSLATION alongside Loopback, Part State and STORE
(the `midi-loopback-translation` test remix does this). Translation starts OFF;
selecting the module alone does not change any emitted MIDI note bytes.

The same ROUTING window adds these controls:

| Encoder | Label | Setting |
| --- | --- | --- |
| A | DEST | Existing route: EXT, INT or BOTH |
| B | RE-MAP | Which destination copy is note-translated: OFF, INT, EXT or BOTH |
| C | SRC REF | Source reference pitch; MIDI 60 is displayed as C4 |
| D | TGT REF | Target reference MIDI note number |
| E | RANGE | Symmetric semitone range around TARGET REF, displayed as ±n |
| F | — | Unused |

RE-MAP is independent of DEST. With DEST BOTH and RE-MAP INT, the internal copy
is translated and the external copy stays raw. RE-MAP does not enable a route.
OFF preserves the normal Loopback behavior. CC, bend, pressure, program changes,
clock and transport are not translated or given any new route.
With RE-MAP OFF, C–E keep their ordinary values and stock controls visible but
ignore encoder turns. Enabling RE-MAP makes them editable again. The translation
view omits the footer to give the stock rotary controls room; A, YES and NO
still close it.

![RE-MAP OFF with inactive mapping controls](../../img/midi-loopback-translation/off.png)
![Internal translation with external MIDI left raw](../../img/midi-loopback-translation/internal.png)

The initial reference/range values are Octatrack-friendly: **C4 → 84**, range
**±12**, accepting **72–96**. Change RE-MAP from OFF explicitly to use them.
C4 sends 84 and D4 sends 86.
The accepted source window is C3–C5 (48–72), inclusive. Notes outside that
window are dropped for the translated copy; they are not clamped or wrapped.
For another target, set both references and a symmetric range manually (0–63
semitones each way, at most 127 notes including the centre). RANGE ±0 accepts
only the source reference. Translated notes outside MIDI 0–127 are also dropped,
never clamped. Asymmetric ranges
are not supported.
The rule is `output = final source note + target reference − source reference`.
Native transpose and generated ARP/Harmony/Follow pitches come before mapping.

Set the source reference yourself. This version has no validated native sample
reference-pitch field and does not inspect audio or infer pitch from filenames.
SOURCE REF and TARGET REF are mapping references, not claims about a sample's
recorded pitch.

Changing an enabled mapping releases held notes at their original output
pitches before applying the new settings. Route, channel and Part changes keep
the same cleanup behavior. Distinct source notes mapping to one destination
channel/pitch share that voice until its last owner releases it.

Translation settings are per MIDI track and Part, including working and saved
Part copies. Use native Part Save/Reload/Copy/Paste/Clear as usual. Use **SAVE
PROJECT** to persist them before power-off: these separate settings do not use
retained SRAM, so unsaved edits are not recovered after a restart.

STORE keeps `lbnt01.work` through `lbnt16.work` beside the native bank files;
project save/reload also maintains their `.strd` counterparts. Keep these files
with the project when copying or backing it up. No file is created for an
untouched project. Missing files mean OFF. Invalid/incompatible files are not
overwritten silently: the existing STORE recovery prompt offers keeping the
file, starting fresh, or backing it up first. Keeping a refused file disables
translation editing/saving for that bank until it is resolved.

This follow-up has software/emulator verification only. It has no physical-device
acceptance; the existing Loopback hardware results do not cover translation.

## Notes

Select MIDI PART STATE alongside MIDI LOOPBACK. This contribution supplies a
standalone test remix; official remix selections are unchanged. MIDI Scenes
needs a later bridge and is currently refused with Loopback.

Held notes are released at their original destination when routes change.
Avoid overlapping internal and external held notes on the same channel/pitch:
the stock receiver merges their held-note state, and the first release ends
the shared note. Independent sustain from each source is not supported. Internal delivery filters out MIDI-track receivers,
so it cannot retrigger a MIDI track through the internal path, even with
matching MIDI/auto-channel assignments. A no-listener internal note-on is
rejected before it can allocate held state without an audio recipient. External echo loops remain
possible when BOTH output returns through a cable or another device; use INT
for internal-only control.
Clock, transport, SysEx and project-wide program-change sync stay global.

Stock 1.40C cold project load resets the destination flags to zero (EXT) in
both working and saved Parts. The native flags field accepts only zero on stock,
whereas MIDI PART STATE allows 0–15; INT/BOTH occupy bits 2–3.
Saving that bank on stock loses its INT/BOTH settings. Other bank files stay
unchanged until saved; keep a separate backup before returning to stock.

The standalone Loopback selection reserves three 6,144-byte sample-arena
pages (18,432 bytes) for runtime code, state and loading. Combined remixes
compute their own reservation from all selected modules.

Sequenced routing follows each MIDI track's applied Part, independently of
an audio voice retaining another Part or a Part selected for editing. Matching
audio and MIDI track numbers do not imply shared playback state.
