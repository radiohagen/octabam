Use one MIDI track's root progression on another track while keeping the
receiver's own rhythm, velocity and note length.

## Controls

- Open MIDI NOTE SETUP with **FUNC + SRC**. Turn **D: RFOL** to choose a source track.
- Press **D** to open FOLLOW. **A** selects RFOL; **B** selects FIXED or SOURCE;
  **C** selects the octave; **D: UPDT** selects TRIG or LIVE.
- **FIXED** uses the source pitch class in a chosen octave. **SOURCE** preserves
  the source register with an octave offset. Receiver TRAN adds chromatic semitones.
- **TRIG** updates at the receiver's next note. **LIVE** also releases and
  retriggers a held sequenced note when the source root changes; its original
  release deadline remains in place.

![RFOL on NOTE SETUP](../../img/midi-follow/source.png)
![FIXED register and TRIG response](../../img/midi-follow/fixed.png)
![SOURCE register and LIVE response](../../img/midi-follow/source-live.png)

## Behavior and limits

- Circular source selections are skipped. Chains use the ultimate source's root.
- Muting the source keeps its progression available to followers. Muting the
  receiver silences that receiver.
- Settings belong to the Part. Root history and held-note ownership are runtime state.
- LIVE does not steal an occupied channel/pitch. A conflicting or out-of-range
  replacement voice is omitted. Separate MIDI channels avoid this ambiguity.
- Saving a Follow project on stock firmware loses register/response settings.
  After returning, RFOL can still be enabled with FIXED octave 0. Keep a backup.
- Requires MIDI Part State. Harmony and Scales are optional integrations.
- Screenshots and automated MIDI captures come from the emulator. Physical
  encoder feel, MIDI timing and external-instrument behavior need hardware checks.
