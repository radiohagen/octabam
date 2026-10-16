# Harmony degree storage

Harmony stores musical roots as scale degrees and octave positions while HARM
is NOTE or CHORD. DEG `1:3` means degree 1 in tonic octave 3.

- Turning HARM on converts native roots to the nearest degree in KEY, ties downward.
- Changing KEY preserves degrees and changes their sounding pitches.
- Switching NOTE/CHORD preserves roots. Turning HARM off writes resolved roots
  into native NOTE and preserves NOT2–4.
- KEY OFF uses C major for degree conversion. TRAN, voicing and root placement
  affect output rather than the stored degree.
- Out-of-range degrees are silent while HARM is active. Conversion to native
  NOTE clamps them to MIDI 0–127.

Part settings hold HARM, KEY, voicing, SIZE and default DEG/CHRD. Pattern locks
remain attached to their patterns. Native NOTE fields hold canonical storage
mirrors while HARM is active, so stock firmware can play different pitches.

Each bank uses `hdegNN.work` and `hdegNN.strd` companions in the project directory.
HDP3 validates the payload and its relationship to the native bank before use.
Missing companions cannot guarantee recovery of the original Harmony data;
incompatible or corrupt companions are protected from overwrite. Earlier Harmony formats are
not migrated. Preserve an older project's files with its matching firmware.

KITS recalls Part defaults; it does not move pattern locks. See
[KITS](KITS.md), [Scenes](SCENES.md) and [Voicing](../VOICING.md).

[Developer notes and verification](DEVELOPMENT.md).
