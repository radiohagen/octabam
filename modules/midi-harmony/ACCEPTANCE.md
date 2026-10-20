# Harmony hardware acceptance

Use the packaged image and a complete copy of a project. Skip KITS and MIDI
SCENES steps in selections without those modules.
Keep the current firmware and original project as the comparison.
The package's source reference and hashes identify the image under test.
Automated checks do not establish hardware timing or hardware acceptance.

## Controls and representation

- MIDI NOTE SETUP, F: HARM selects OFF, NOTE or CHORD.
- In HARM NOTE or CHORD, MIDI NOTE page A is DEG, displayed as `degree:octave`.
  One detent advances one scale position; degree 7 advances to degree 1 in the
  next tonic octave. FUNC + A changes only the octave, including on held
  steps and Scene root locks. Hold a trig to edit its degree; push A to unlock it.
- In HARM CHORD, D is CHRD. In HARM NOTE, D/F are inactive.
  E remains ACC in both modes; hold trigs to edit or toggle its step locks.
- ARP KEY selects the tonic and scale. KEY OFF uses C major as the reference
  for degrees. Without a selected scale, TRI retains its major chord recipe.
- OFF restores the native NOTE page. NOT2–4 retain their native stored values.
  TRAN and arranger transpose remain output offsets; conversion does not bake
  them into DEG or NOTE.

`1:3` resolves to C3 in C minor and D3 in D minor. `7:3` resolves to B-flat3
in C minor and C4 in D minor: the octave belongs to the tonic, not each
resolved note's letter name.

Use `1:3` whenever a fresh or missing degree needs a default. Existing stock
notes are still converted when entering HARM; the default does not replace
the music already in a Part or sequence.

## Acceptance sequence

1. Change HARM on NOTE SETUP and press YES; confirm it remains set.
   On a MIDI track, choose C minor, HARM CHORD and CHRD TRI. Program three
   trigs with `1:3`, `4:3`, `5:3`. Confirm Cm–Fm–Gm.
2. Change KEY to D minor. Confirm Dm–Gm–Am and unchanged DEG values. Return
   to C minor and confirm the exact original progression. Repeat with a
   different mode; TRI should adapt its intervals, explicit MIN should not.
3. Return to D minor. Change CHORD to NOTE: the same roots should play singly.
   Change to OFF: the first stored root should now be D3. Change KEY to
   C major while OFF, then enable HARM: the first root should be `2:3`, D3.
4. Repeat with nonzero TRAN, ROOT -1 OCT, an inversion and an open spread.
   Confirm that the stored root conversion remains D3, independent of those
   output treatments. Check a sequence arp and held live keys while changing
   HARM, then STOP. Listen for doubled transpose or stuck notes.
5. Edit and unlock degrees while holding trigs. Copy/paste a step, track and
   pattern; clear and undo them. Delete and replace a trig. An unlocked root
   must follow the Part default, and an old deleted degree must not reappear.
6. Use different Part KEYs. Save a Part, change its DEG default, reload it,
   copy it and clear it. Switch banks. Confirm the intended degree defaults
   and explicit root locks stay attached to the correct data.
   With KITS, save two Kits with different DEG/CHRD defaults, HARM, KEY,
   voicing settings. Unlocked trigs must inherit the incoming Kit;
   explicit DEG and CHRD locks remain pattern data. Load, undo, copy, clear,
   quick-save and reload the Kits, including one from another bank.
   Specifically, load D-minor OFF over C-minor CHORD with an explicit `1:3`:
   the locked native NOTE must become C3, while unlocked trigs use the incoming
   Kit's NOTE. Repeat while playing, with held keys and an arp, then STOP.
7. Record roots and chord-quality changes live, including two changes on one
   step. Change KEY before replay: the recorded degrees should transpose,
   and the final recorded change should win. Check releases with overlapping
   notes and after changing the selected track.
8. Save the project, reload it, use Save To New, and power-cycle after an
   unsaved current-bank edit. Confirm both DEG and CHRD, then play the result.
9. Set ACC +1, LOW 0 and HIGH 7. Repeat a short pattern and confirm each
   step starts unshifted, then advances independently. Lock one step OFF and
   another -1; clear those locks and confirm default inheritance. Test WRAP,
   BOUNC, HOLD and ZERO at both limits, and NONE/START/PAT/BOTH reset policies.
   Rests and suppressed steps must not advance; arp repeats must not advance
   twice. Save/reload and retained restart must keep settings and locks while
   starting runtime offsets at zero. In HARMONY, check CHORD/ACCUM navigation,
   all four displayed encoders, and inactive E/F positions.
10. Switch HARM OFF and compare ordinary note editing, NOT2–4, recording,
    copying and playback with the current firmware on the original project.
11. With MIDI SCENES, assign scenes A/B and hold each scene while turning MIDI NOTE
    page A. Set different DEG endpoints, sweep the crossfader, then change
    KEY. Confirm scale-relative roots, unchanged scene degrees and balanced
    releases. Repeat with CHORD and an arp, including several MIDI tracks.
    Leave one endpoint empty and check inheritance from the pattern/Part.
12. Save and reload those scenes, power-cycle, then recall resident and
    other-bank Kits while playing and holding keys. Confirm incoming scene
    roots, DEG/CHRD defaults and no stuck notes. Switch OFF and back to HARM;
    confirm native NOTE/degree conversion. Holding a scene must not edit
    CHRD or dormant NOT2–4 while HARM is active.

Record the displayed build, device model, receiving synth, steps performed,
actual notes and any timing or release issue. Retain the exact failing project
copy and its companion files if a case fails.

MIDI Follow integration needs a separate bridge and is outside this PR's
acceptance scope.

## Storage and boundaries

The candidate writes `hdegNN.work` / `hdegNN.strd` companions alongside native
bank files. Back up and move the entire project. Existing CHRD companions are
not imported into this new format. Keep test projects separate when switching
between the current implementation and this candidate.

Malformed or mismatched companions are rejected before publication. A rejected
working save must not replace the stored bank/companion backup. Native bank and
companion writes are separate filesystem operations; this does not make stock
project saving an atomic transaction across an arbitrary power loss. Recover
the complete stored pair, not one file from each save.

Degrees resolving beyond MIDI 0–127 are silent in HARM. Turning HARM OFF
commits the closest MIDI boundary because native NOTE has no separate silent
root value. KITS carries native Part defaults; it adds no degree storage or
conversion adapter. The Scenes adapter uses upstream's full-table API; see [SCENES.md](SCENES.md).
It does not store scene locks in native LFO designer bytes. Include LFO designer
playback in hardware acceptance when it is part of the performance project.
