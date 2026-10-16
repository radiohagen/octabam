# MIDI Harmony

Turns scale-degree roots into notes or chords using the MIDI ARP KEY, with
inversions, automatic voice leading, spread and root placement.

## Start playing

1. Set the MIDI track's output channel and choose **KEY** on **ARP SETUP**
   (**FUNC + AMP**). MIDI Scales adds five more modes to Major and Minor.
2. Open **NOTE SETUP** with **FUNC + SRC** and turn **F: HARM**:

| HARM | Result |
| --- | --- |
| OFF | Native NOTE and NOT2–4. |
| NOTE | One scale-degree root; the NOTE page shows DEG. |
| CHORD | A chord from that root; the NOTE page shows DEG and CHRD. |

3. Program DEG 1, 4 and 5 on three trigs. In C minor with CHRD TRI, these
   play Cm, Fm and Gm. Changing KEY to D minor gives Dm, Gm and Am.

DEG `1:3` means degree 1 in tonic octave 3. Turn DEG to move through the scale;
**FUNC + DEG** changes only the octave. Hold steps to edit DEG/CHRD locks;
press the corresponding encoder while holding steps to toggle the locks.

Press **F** on NOTE SETUP to open **HARMONY**:

| Control | Choices |
| --- | --- |
| VOIC | ROOT, AUTO voice leading, 1ST, 2ND or 3RD inversion. |
| SPRD | CLOSE, OPEN or WIDE. |
| ROOT | KEEP, OMIT, -1 OCT or -2 OCT. |
| SIZE | NAT recipe size, or 2, 3 or 4 voices. |

These are track settings. Existing held notes retain their original releases.
See [Voicing](VOICING.md) for the musical rules.

## Chord Play

With HARM CHORD, select **CHORD PLAY** using FUNC + UP/DOWN.

- Trigs 1–8 play scale roots from tonic to the next octave.
- Trigs 9–16 select TRI, 7TH, ADD9, SUS2, SUS4, MAJ, MIN and DOM7.
- Pressing a variation changes held chords immediately. Releasing it is silent;
  the next root uses the latest still-held variation, or the base CHRD.
- Live recording stores root degree and chord choice, not generated chord tones.
- FUNC + LEFT/RIGHT changes the playing octave. The display shows the sounding chord.

TRI/7TH/ADD9/SUS choices follow the scale. Explicit MAJ/MIN/DOM7 keep their
chromatic intervals. KEY OFF uses C major for degree mapping. With Follow,
the root and KEY come from the source; rhythm and chord settings remain local.

## Storage and compatibility

HARM, KEY, voicing, SIZE and default DEG/CHRD are native Part settings.
Pattern DEG/CHRD locks live in the project's `hdeg01.work`–`hdeg16.work` and
their `.strd` companions. Keep them with the project. Incompatible companions
are protected from overwrite; earlier Harmony formats are not migrated.

Turning HARM OFF writes resolved roots back to native NOTE. It preserves
NOT2–4 but does not render generated chords into those fields.

**Keep a separate project copy for stock firmware.** With HARM active, native
NOTE fields are storage mirrors and can play different pitches on stock.
Stock also resets voicing/spread/root choices and clamps extended KEY modes
to B Minor; saving persists those changes for the bank written.

Requires **MIDI Part State** and **STORE**. PLOCKS P2 requires the **Harmony
PLOCKS bridge** and compatible retention settings. KITS libraries are per
project; recalling a kit supplies Part defaults while pattern locks stay with
the patterns. See [storage](degrees/README.md) and [KITS](degrees/KITS.md).

[Implementation, provenance and verification](DEVELOPMENT.md).
