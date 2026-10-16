Play and sequence scale-degree roots and chords using the native MIDI ARP KEY.
Changing KEY transposes a degree progression into the new key.

## Controls

- Open MIDI NOTE SETUP with **FUNC + SRC**. **F: HARM** selects OFF, NOTE or CHORD.
- **OFF** uses native notes. **NOTE** plays one degree root. **CHORD** generates
  a chord from that root; the main NOTE page shows **DEG** and **CHRD**.
- Press **F** to open HARMONY: HARM, VOIC, SPRD, ROOT and SIZE.
- Hold sequencer steps to edit DEG or CHRD locks. FUNC + DEG changes the octave.
- Select **CHORD PLAY** with FUNC + UP/DOWN. Trigs 1–8 play roots; trigs 9–16
  choose chord variations. Live recording stores the root and chord choice.

![HARM CHORD on NOTE SETUP](../../img/midi-harmony/setup.png)
![Harmony voicing controls](../../img/midi-harmony/voicing.png)
![Degree and chord editing](../../img/midi-harmony/degrees.png)
![Chord Play layout](../../img/midi-harmony/chord-play.png)

## Storage and composition

- Part settings hold HARM, KEY, voicing, SIZE and default DEG/CHRD.
- Pattern locks use `hdeg01.work`–`hdeg16.work` and their saved `.strd`
  companions. Keep these files with the project. Incompatible or corrupt
  companions are protected from overwrite.
- Requires MIDI Part State and STORE. Follow and extended Scales are optional.
- Stock cannot interpret Harmony's degree/chord data. Native NOTE storage
  mirrors can play different pitches on stock. Stock also resets voicing,
  spread and root-placement settings, and clamps extended KEY modes to B Minor.
  Saving on stock persists those changes; keep a separate project copy.
- PLOCKS integration requires the Harmony PLOCKS bridge and a compatible
  retention layout. The combined test remix selects MIDI TRACK with MIDI SRAM.
