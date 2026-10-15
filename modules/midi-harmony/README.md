# MIDI Harmony

MIDI Harmony supplies scale-degree roots, generated chords and CHORD PLAY.
Include `MIDI HARMONY`, `MIDI PART STATE` and `STORE` in a remix.
MIDI FOLLOW and MIDI SCALES are optional. Degree support is part of Harmony;
there is no separate module to select.

Open MIDI **NOTE SETUP** with **FUNC + SRC**. Turn **F: HARM**:

| HARM | Main NOTE page | Output |
| --- | --- | --- |
| OFF | Native NOTE / NOT2–4 | Stock playback |
| NOTE | A: DEG | One scale-degree root |
| CHORD | A: DEG, D: CHRD | Chord built from that root |

Choose **KEY** on **ARP SETUP F** (FUNC + AMP). MIDI SCALES adds five modes
to stock Major/Minor. DEG reads `1:3`: degree 1, tonic octave 3. Turning A
advances through the scale; **FUNC + A changes only the octave**. Hold steps
to edit their DEG locks; press A while holding steps to toggle those locks.
FUNC octave editing also works on held steps and MIDI Scene root locks.

Changing KEY preserves stored degrees. For example, 1–4–5 in C minor plays
Cm–Fm–Gm; changing KEY to D minor plays Dm–Gm–Am. Turning HARM on converts
native roots to the nearest scale degree (ties downward). Turning it OFF
materializes resolved roots as native NOTE. NOTE ↔ CHORD preserves degrees.
KEY OFF uses C major for degree mapping and unscaled chord recipes. Native
NOT2–4 remain stored and become active again in OFF. A degree resolving
outside MIDI 0–127 is silent; OFF conversion clamps to that native range.

Press **F** on NOTE SETUP to open **HARMONY**:

| Knob | Setting | Values |
| --- | --- | --- |
| A | HARM | OFF / NOTE / CHORD |
| B | VOIC | ROOT / AUTO / 1ST / 2ND / 3RD |
| C | SPRD | CLOSE / OPEN / WIDE |
| D | ROOT | KEEP / OMIT / -1 OCT / -2 OCT |
| E | SIZE | NAT / 2 / 3 / 4 |

F is inactive. YES, NO or F closes the window; track/page keys close it
before changing selection on a second press. Edits apply immediately. YES
on NOTE SETUP preserves RFOL and HARM while confirming stock staged fields.
Fresh Parts use HARM OFF, DEG `1:3`, CHRD TRI and ROOT/CLOSE/KEEP voicing and SIZE NAT.

Generated notes enter the stock arp. Sequenced TRAN/P-locks apply once before
chord generation; scale-derived qualities receive final scale correction.
Explicit MAJ/MIN/DOM7 retain their chromatic tones. Live keys use stock TRAN
behavior: none with arp OFF, current TRAN and arranger offset with arp ON.
Live recording captures one root degree and CHRD per played event, never
extra chord tones in NOT2–4. Live keys do not replace a running pattern's root.

With MIDI FOLLOW, the receiver keeps its rhythm, HARM, CHRD, voicing and TRAN.
Its root and effective KEY come from the ultimate source, before voicing or
ROOT placement; MODE/OCT sets the receiver's register. Source KEY is shown
read-only on the receiver. Held notes retain their original release identity.

## First playing workflow

1. Select a MIDI track and set its output CHAN to the instrument.
2. Choose KEY on ARP SETUP, then HARM CHORD on NOTE SETUP.
3. Program DEG 1, 4 and 5 on three trigs. Leave CHRD at TRI and play.
4. Change KEY: the progression retains its degree shape in the new key.
5. Select CHORD PLAY with FUNC + UP/DOWN to play roots and variations by hand.
   Live recording writes root and quality, so the sequence remains editable.

CHORD PLAY is a playing mode. The upper eight variation keys are held
modifiers with the release behavior described below; they are not an arm switch.

## CHORD PLAY and CHRD

Set HARM to CHORD, then return to the main MIDI NOTE page. D displays CHRD
in the old NOT2 position; E/F are inactive. Native NOT2–4 values remain stored
and become available again with HARM OFF. Turning D alone selects the live
chord. The CHRD knob displays this base value during performance; temporary
extensions appear in the sounding-chord guide. Hold one or more sequencer steps and turn D to edit their CHRD locks;
press D while holding steps to toggle their locks. Unlocked steps display
and play the current Part's base CHRD, independently of the previous step.

Choose CHORD PLAY with the normal FUNC + UP/DOWN mode selector. Outside grid
recording, trigs 1–8 play the selected scale from tonic through the next octave.
With KEY OFF they use C–D–E–F–G–A–B–C as roots; each TRI is major.
The stock-style inverted title bar reads CHORD PLAY when idle and shows the
actual MIDI notes while sounding. Chord names and note names both use sharps.
A compact line below the chord name always shows SIZE, VOIC, SPRD and ROOT:
`N:4 V:1 S:O R:-1` means four notes, first inversion, OPEN spread,
root down one octave. N:N means SIZE NAT.
VOIC uses R/A/1/2/3 (ROOT/AUTO/inversions), SPRD C/O/W, and ROOT
K/O/-1/-2 (KEEP/OMIT/octave drops). Long add9 names omit parentheses here
to leave this settings line visible.
FUNC + LEFT/RIGHT uses the chromatic octave controls. Trigs 9–16 temporarily
select these choices, in fixed positions:

| Key | CHRD | Notes, before global voicing |
| --- | --- | --- |
| 9 | TRI | Scale degrees 1, 3, 5 |
| 10 | 7TH | Scale degrees 1, 3, 5, 7 |
| 11 | ADD9 | Scale degrees 1, 3, 5, 9; four voices |
| 12 | SUS2 | Scale degrees 1, 2, 5 |
| 13 | SUS4 | Scale degrees 1, 4, 5 |
| 14 | MAJ | Root + 0, 4, 7 semitones |
| 15 | MIN | Root + 0, 3, 7 semitones |
| 16 | DOM7 | Root + 0, 4, 7, 10 semitones |

The last pressed variation takes effect immediately and retriggers held roots.
Releasing a variation is silent: the sounding quality stays latched until a
new root is pressed. That new root uses the newest still-held variation, or
D's base CHRD when no variation remains held. There is no carry-over latch
across root presses. In C minor: hold G for Gm, press MAJ for G major, release
MAJ (no new notes), then press DOM7 for G7. Releasing DOM7 then G sends no new
note-ons; the next G starts as Gm. With live recording active, only presses
that sound a chord create root-plus-CHRD trigs; releases do not record an
intermediate return to the base. Same-step changes leave the final choice.
Generated chord tones are never recorded into NOT2–4.

The LCD shows the resulting chord name below CHORD PLAY, leaving the native
footer intact. Root and variation groups use opposite trig LED channels; a held
key uses both. Physical colors and brightness require hardware acceptance.
Names use sharps. Scale alterations are retained:
in C minor, D ADD9 is Ddim(addb9), and D SUS2 is Dsusb2b5. Explicit qualities
bypass the final scale correction: G DOM7 remains G–B–D–F in C minor.

Grid recording keeps the normal 16-step layout and the guide follows the
sounding sequence. Rests and STOP clear the chord name and pitches. SIZE, VOIC, SPRD and ROOT remain
track-wide controls in the Harmony window; they are not CHRD locks. Follow
inherits roots and scales as before, while every follower resolves its own
CHRD. Live playing does not take over a running leader pattern.

PAGE retains its native behavior. Direct CHORD PLAY sends the complete chord
immediately; no deferred note scheduler is installed.

## Chord size

SIZE chooses the sounding voice count; VOIC chooses root position, an inversion
or AUTO voice leading; SPRD opens the spacing; ROOT keeps, omits or lowers the
logical root. They affect the next chord; existing notes keep their releases.
NAT preserves each chord recipe's count. Fixed SIZE 2/3/4 prioritizes the tones
that identify the chord, then uses octave doublings where needed.

See [Voicing](VOICING.md) for the exact reduction, inversion, AUTO, spacing,
register-limit and root-placement rules, with examples. AUTO is a bounded
movement-minimizing heuristic, not a classical part-writing engine.

## Storage and validation

HARM, DEG, CHRD, SIZE, KEY, voicing and Follow settings live in each native Part.
UI edits use the selected Part; playback uses each track's playing Part.
Part/Kit recall supplies incoming defaults; explicit DEG/CHRD locks stay with
patterns. Runtime roots, note ownership and AUTO history are not persisted.

Keep `hdeg01.work`–`hdeg16.work` and their `.strd` companions with the project.
They store pattern DEG/CHRD locks in compact HDP3 format. There is no migration
from earlier Harmony formats or project-comment settings. Start with a project
copy without older `hdeg` companions; incompatible files block overwriting saves. See [degree storage](degrees/README.md) for the
layout, failure handling and native boundary rules, [KITS](degrees/KITS.md)
and [MIDI Scenes](degrees/SCENES.md) for composition details. Combining Harmony with PLOCKS P2 requires the HARMONY PLOCKS bridge and
compatible retention settings; their unadapted hooks overlap. For this branch's track-local experiment, select MIDI SRAM and Harmony `MIDI TRACK`;
PLOCKS P2 and MIDI SCENES keep their upstream storage.
The resource ledger rejects conflicting allocations.

Run `make check REMIX=harmony-degrees` for the minimal verification carrier.
For a prepared local project copy, run the full firmware gates:

```sh
.venv/bin/python tools/verify/verify_harmony_degree_port.py --project /path/to/project
.venv/bin/python tools/verify/verify_chord_display.py --project /path/to/project
.venv/bin/python tools/verify/verify_midi_setup_port.py --project /path/to/project
```

The manifest declares linked-code gates for routing, voicing, ownership,
recording, native Part publication, degree boundaries and companion storage.
See the [hardware acceptance sequence](degrees/ACCEPTANCE.md) for instrument
checks. Emulator results do not establish physical MIDI timing or battery retention.

The SIZE gate executes generated ColdFire code (`verify_harmony_size.py`);
`verify_harmony_size_port.py --project DIR` checks real firmware output.
Regenerate `size.s` with `python3 modules/midi-harmony/generate.py` and verify
with `--check`; edit the C source, never its generated assembly.

## Shared project storage

Harmony is a STORE client (`ch_st_*` in `chord-files.s`). STORE owns native
save/load/new-project/CS1/copy hooks and preserves the original caller
identity. Harmony reads HDP3 after native banks and KITS, snapshots its own
retained allocation, and returns errors through STORE's checked callbacks.
A failed companion save blocks native bank and P2 backup writes. The pattern
and track copy bridge remains separate because it carries live MIDI/audio
editing state, not project-file operations. HDP3, HDN3 and P2 capacities are
unchanged by this registration.
