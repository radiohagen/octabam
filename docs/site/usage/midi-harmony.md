## Playing a progression

MIDI Harmony lets a pattern store scale degrees and chord choices. Program
1, 4 and 5, choose C minor in **ARP SETUP → KEY**, and the progression plays
Cm, Fm and Gm. Change KEY to D minor and the same pattern plays Dm, Gm and Am.
Rhythm, velocity, note length and the stock arpeggiator remain track controls.

Open **NOTE SETUP** with FUNC + SRC. Turn **F: HARM** to NOTE for one
scale-degree root, or CHORD for generated chords. OFF uses native note editing.

![HARM mode](../../img/midi-harmony/setup.png)

## Roots and chords

On NOTE MAIN, **DEG** replaces NOTE. `1:3` means degree 1 in tonic octave 3.
Turn the encoder to move through the scale; FUNC + DEG changes the octave.
In CHORD mode, **CHRD** selects the recipe. Hold trigs to lock DEG or CHRD;
press their encoder while holding trigs to toggle locks.

![Degree and chord controls](../../img/midi-harmony/degrees.png)

TRI, 7TH, ADD9, SUS2 and SUS4 follow the scale. MAJ, MIN and DOM7 keep their
chromatic intervals. KEY OFF uses C major for degree mapping.

## Voicing

Press F on NOTE SETUP to open HARMONY. On the CHORD page, A selects root
position, automatic voice leading or an inversion; B selects spread; C keeps,
omits or lowers the root; D selects recipe size or two, three or four voices.
These settings affect CHORD mode. Existing notes retain their original releases.

![Voicing controls](../../img/midi-harmony/voicing.png)

## Accumulating degrees

NOTE MAIN **E: ACC** sets OFF or an amount from −7 to +7 degrees. A sounding
step starts unshifted, then advances its next occurrence. Rests, failed
conditions and suppressed notes do not advance it. Arp repeats and chord voices
share that occurrence's shift. Live keyboard notes do not accumulate.

Hold trigs to set independent ACC locks. An unlocked step inherits the pattern
track default; an OFF lock explicitly disables accumulation on that step.

Choose ACCUM in HARMONY with UP/DOWN. LOW (−21…0) and HIGH (0…21) set inclusive
limits. BOUND chooses wrap, bounce, hold at the limit, or return to zero.
RESET chooses none, start/resume, pattern change, or both. Changing the amount
resets that step; changing limits or policy resets the track's running offsets.

![Accumulator controls](../../img/midi-harmony/accumulator.png)

## Chord Play

With HARM CHORD, select CHORD PLAY using FUNC + UP/DOWN. Trigs 1–8 play scale
roots; 9–16 select TRI, 7TH, ADD9, SUS2, SUS4, MAJ, MIN and DOM7. Variation keys
change held chords immediately. Live recording stores the degree and chord
choice. FUNC + LEFT/RIGHT changes the playing octave.

![Chord Play](../../img/midi-harmony/chord-play.png)

## Saving and compatibility

HARM, KEY, voicing and default DEG/CHRD belong to the Part. Pattern locks and
ACC configuration save with the project's `hdeg01.work`–`hdeg16.work` files
and their `.strd` companions. Keep these with the project. Running accumulator
offsets restart at zero after load or power-on.

Keep a separate project copy for stock firmware: active Harmony patterns can
play different notes there, and stock saves can reset extended settings.
Turning HARM OFF writes resolved roots into native NOTE; it does not render
generated chords into NOT2–4.

This test selection requires MIDI Part State, MIDI SRAM and STORE. EUCLID
uses the same transport hooks and cannot be selected with it. PLOCKS P2 and
MIDI Follow need additional composition bridges, outside this standalone selection.
Hardware testing remains outstanding.
