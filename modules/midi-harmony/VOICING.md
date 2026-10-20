# Harmony voicing reference

Detailed musical rules for [MIDI Harmony](README.md). Start with the module
README for controls, recording and the first playing workflow.

## Chord size

SIZE sets how many distinct MIDI pitches Harmony sends to the stock arp.
NAT keeps the original chord recipes, inversions, ROOT behavior and AUTO
history rules. Fixed 2/3/4 counts use the following rules instead. They affect
HARM CHORD only and apply on the next trigger; held notes retain their releases.

First choose the chord tones. Keep the root unless ROOT is OMIT. Prioritize
the seventh/ninth for 7TH/DOM7/ADD9, or the suspension for SUS2/SUS4. Next keep
an altered fifth if present, then the third and ordinary fifth as space allows.
A plain triad prioritizes its third; a diminished triad prioritizes its b5.
This is a deterministic reduction, not a reharmonization or classical
part-writing engine. Two-note reductions necessarily leave some identity implied.

| Chord, ROOT KEEP | SIZE 2 | SIZE 3 | SIZE 4 |
| --- | --- | --- | --- |
| TRI / MAJ / MIN, ordinary fifth | Root + third | Complete triad | Triad + octave doubling |
| SUS2 / SUS4 | Root + suspension | Complete chord | Chord + octave doubling |
| 7TH / DOM7, ordinary fifth | Root + seventh | Root + third + seventh | Complete chord |
| ADD9, ordinary fifth | Root + ninth | Root + third + ninth | Complete chord |

For an altered-fifth seventh/add9 at SIZE 3, retain root, altered fifth and
extension, leaving out the third. SIZE 4 retains all four tones. ROOT OMIT
removes the root from consideration before selection: a normal seventh at
SIZE 2 gives third + seventh; a triad gives third + fifth. Scale-derived
alterations stay intact; no new chord tones are invented.

Invert the **retained distinct tones**, place a dropped ROOT if requested,
then fill spare voices with octave copies, starting from the actual bass
and working upward. Doublings do not
create additional inversions. An unavailable inversion uses the last one:
3RD on a three-tone chord uses 2ND; 2ND/3RD on two tones use 1ST.

| C major, SIZE 4 / CLOSE / KEEP | Sounding pitches |
| --- | --- |
| VOIC ROOT | C3–E3–G3–C4 |
| VOIC 1ST | E3–G3–C4–E4 |
| VOIC 2ND or 3RD | G3–C4–E4–G4 |

SPRD operates on the expanded chord. OPEN raises the second-lowest note an
octave; if a doubling already occupies that pitch, use the next free octave.
WIDE raises every note above the bass an octave. For two voices, OPEN and
WIDE are equivalent. A spread that exceeds MIDI 127 falls back to CLOSE.
ROOT -1/-2 OCT places one root at the requested lower register; a spare voice
can double that root above it. For example, C3–E3–G3 at SIZE 4 / ROOT -1 OCT
becomes C2–C3–E3–G3. SIZE therefore remains the **sounding**
count with KEEP, OMIT or a dropped root. When MIDI limits make that impossible,
sound fewer notes and reset AUTO history; never wrap or add an unrelated tone.

Fixed SIZE AUTO first opens crowded low notes by octaves and excludes an ADD9
ninth from the bass. It then compares the final sorted sounding notes,
including doubling, spread and root placement. It minimizes total semitone
movement among these candidates, then prefers
more stationary voices. Equal scores prefer root position, then earlier
inversions and octave offsets 0/-12/+12. It searches at most twelve candidates,
keeps the bass near the requested register and retains the exact root with
KEEP (or the exact lowered root with a drop). Chord-quality changes keep
history: C3–E3–G3 can become C3–E3–B3 when TRI changes to 7TH at SIZE 3.
At low registers, SIZE 2 moves C–E to C–B rather than a crowded B–C.
The spacing policy is conservative: below MIDI 48, leave at least seven
semitones above the bass and five between other low voices; below MIDI 60,
leave at least three. Higher voices may use seconds. Manual VOIC remains
literal, and the requested root anchor never moves to repair another voice.
Changing SIZE resets history; other settings, source/scale, Part replacement
and deliberate octave jumps follow the same boundaries as NAT. There is no
promise to avoid parallel intervals or resolve classical tendency tones.

SIZE is a per-track Part default, not a parameter lock. CHRD locks still
select chord identity; SIZE determines its realization. The guide displays
the requested chord name and actual sounding pitches; a reduced voicing can
omit a tone implied by that name. Native Part Save/Reload, copy and KITS recall
carry SIZE. Old valid CHRD bytes select NAT. Pattern HDP4/HMT2 storage and the
10,400-byte retained reservation are unchanged. Older firmware does not decode
the newly packed CHRD/SIZE byte; use a project copy when testing this candidate.

The musical audit uses [Open Music Theory's Jazz Voicings guide](https://viva.pressbooks.pub/openmusictheorycopy/chapter/jazz-voicings/)
as a reference for stable doubling, reduced seventh chords, register spacing
and smooth upper lines. The numeric spacing limits above are our implementation
policy, not thresholds stated in the guide. The actual ii–V–I upper voices are
F–C → F–B → E–B, both with a generated bass and with ROOT OMIT. Two total voices
with ROOT KEEP cannot retain root, third and seventh together; use SIZE 3, or
SIZE 2 / ROOT OMIT with a separate bass, for that shell. Altered-fifth reductions
remain a deliberate tradeoff because three voices cannot retain all four tones.

`verify_harmony_size_musical.py --audio` executes the linked firmware and writes
the actual note sequences, a standard MIDI file and a neutral WAV rendition to
`out/harmony-size-musical/`. This is an audition aid, not a device recording.

## Manual inversions

The following sections describe SIZE NAT unless stated otherwise.

VOIC ROOT keeps the generated root-position chord. 1ST, 2ND and 3RD rotate
one, two or three lower chord tones upward by an octave. With CLOSE spacing,
C3–E3–G3 becomes E3–G3–C4 (1ST) or G3–C4–E4 (2ND). For C3–E3–G3–B3,
3RD gives B3–C4–E4–G4. On a triad, 3RD uses 2ND; changing back to 7TH
restores the selected 3RD inversion. SPRD applies after inversion.

Manual inversions affect the next triggered chord, including the stock arp,
and do not use previous-chord history. The logical root and the recorded
physical key are unchanged. If an inversion exceeds MIDI 127, keep root
position and apply SPRD if it fits; an already incomplete chord keeps the
generator's omission behavior. Existing ROOT/AUTO projects keep their choices.
HARM, SIZE, VOIC, SPRD and ROOT are track defaults, not parameter-lock destinations.

## Automatic voice leading

With HARM CHORD and VOIC AUTO, each track remembers its previous generated
chord and chooses a nearby inversion for the next one. With CLOSE spacing,
C3–E3–G3 followed by F produces C3–F3–A3. The harmonic root is still **F**:
Follow gets F, and recording the physical F key captures its degree. Neither
the lowest voiced note nor the last generated chord tone replaces the root.
Voicing is applied before the stock arp, which therefore plays the chosen
inversion too. A follower with its own HARM CHORD and VOIC AUTO chooses its
own inversions, using the inherited root and scale.

Deliberate octave jumps move the voicing too: C3 → C4 raises every voice
one octave, including an already inverted or OPEN/WIDE chord. Before scoring,
AUTO shifts its previous chord by the whole-octave portion of the logical
root's change (toward zero: +12…+23 means +12; −12…−23 means −12).
Smaller root changes keep ordinary voice leading; crossing B3 → C4 does not
force an octave jump. MIDI limits still apply. This uses transient history
only; project settings and recorded notes are unchanged.

AUTO keeps the exact requested root pitch in every candidate; ROOT can still
lower or omit it afterward. Repeated roots keep their previous voicing.
The bounded search considers each inversion at octave offsets 0, -12 and
+12. Each starts as a compact inversion within one octave, then applies the
selected spread. Every sounded candidate must remain inside MIDI 0–127 and
have its lowest note within one octave of the requested root. It first
minimizes total semitone travel between corresponding sorted **sounded** voices, then
prefers more unchanged voices. Exact ties prefer root position, then earlier
inversions and offsets in the listed order. At most twelve candidates
of four voices are considered per chord; there is no unbounded search.

The first chord uses root position with the selected spread. History is per track and shared between
that track's keyboard and sequence. HARM/VOIC/SPRD/ROOT edits, project load,
and boot reset it; a changed effective scale/source or chord quality/count
reseeds it on the next chord. A truncated high-MIDI chord keeps the existing
voice-omission behavior and resets history. Silence/STOP alone does not reset
history; set VOIC ROOT then AUTO to deliberately reseed it. AUTO is dynamic:
the same stored root can receive a different inversion after a different
preceding chord. Held keys retain their original note-offs when settings change.
VOIC and SPRD have no effect in HARM OFF/NOTE.

## Chord spacing

SPRD sets the spacing of the chosen inversion, independently of manual/AUTO voicing:

| SPRD | Rule | C triad, VOIC ROOT | C seventh, VOIC ROOT |
| --- | --- | --- | --- |
| CLOSE | Keep the compact chord | C3–E3–G3 | C3–E3–G3–B3 |
| OPEN | Raise the second-lowest voice one octave | C3–G3–E4 | C3–G3–B3–E4 |
| WIDE | Raise every voice above the bass one octave | C3–E4–G4 | C3–E4–G4–B4 |

AUTO evaluates movement **after** applying this spacing. OPEN and WIDE may
therefore choose a different inversion from CLOSE. The bass stays near the
requested root while the upper voices can extend into the next octave.
Octave moves preserve the scale and chord identity; Follow still gets the
harmonic root and recording captures the physical key as one degree.

If a complete chord's root-position spread exceeds MIDI 127, its initial
chord falls back to CLOSE. Subsequent AUTO chords may find another valid
spread inversion; if none fits, they also fall back to CLOSE. An already
truncated chord keeps the generator's existing omitted voices. No notes
wrap or clip to a different pitch class. Changing SPRD affects the next
chord trigger; held notes retain their original release pitches. It resets
that track's AUTO history, so the next chord starts in root position.

## Root placement

ROOT shapes the existing harmonic root after inversion and spread. It never
adds a fifth voice. For a C4 major seventh chord with VOIC ROOT/SPRD CLOSE:

| ROOT | Sounded notes |
| --- | --- |
| KEEP | C4–E4–G4–B4 |
| OMIT | E4–G4–B4 |
| -1 OCT | C3–E4–G4–B4 |
| -2 OCT | C2–E4–G4–B4 |

KEEP retains the complete voiced chord. OMIT removes the harmonic root pitch
class wherever the inversion places it. -1 OCT and -2 OCT replace that root
with the generated logical root minus 12 or 24 semitones: the anchor is the
root before inversion/spread, not the lowest voiced note. The other chord
tones keep their pitches. For C4 major with VOIC 2ND, G4–C5–E5 becomes
C3–G4–E5 with -1 OCT. The resulting pool enters the stock arp normally;
there is no separate bass channel or special sustained-bass behavior.

Only HARM CHORD uses ROOT, including with KEY OFF. NOTE and OFF stay
unchanged. MIDI Follow still receives the original harmonic root and live
recording captures the physical key as one degree. AUTO optimizes and remembers
the full underlying chord before ROOT placement, as it previously did for
OMIT. Changing ROOT resets that track's AUTO history and affects the next
chord trigger. Already-held keys retain their original release pitches.

If the requested low root falls below MIDI note 0, it is omitted; it never
wraps or clamps to an unrelated pitch. Other available chord tones continue.
At the high MIDI limit, ROOT placement acts on the available tones, retaining
the generator's omission of unavailable upper voices. An empty OMIT result
remains silent with balanced key/recording ownership and a safe arp pool.

ROOT is a per-track Part setting, not a parameter-lock destination.
