# Playing related MIDI parts

These modules let the Octatrack play a small ensemble: one track supplies a
harmonic direction, while other tracks keep their own rhythms, registers and
sounds. The design keeps the native sequencer, arpeggiator, Parts and controls
as the working surface. You can select the features separately in a remix.

## Three musical jobs

| Module | Player decision | What remains your own |
|---|---|---|
| [MIDI Scales](../../modules/midi-scales/README.md) | Which key and mode should constrain the notes? | Your notes, rhythm, velocity and arp |
| [MIDI Follow](../../modules/midi-follow/README.md) | Which track supplies this track's harmonic root? | Receiver rhythm, register, transpose and instrument |
| [MIDI Harmony](../../modules/midi-harmony/README.md) | How should one root become a note or chord? | Root sequence, quality locks, voicing and performance gestures |

Scales extends the native KEY choice to seven diatonic modes in all twelve
keys. Follow selects a track by RFOL, independently of its output channel.
Harmony stores roots as degrees, generates chords and provides CHORD PLAY.
None requires an audio effect or a separate MIDI processor.

## Start with a chord track and a bass

1. Give MIDI T1 and T2 suitable output channels for two instruments.
2. On T1, choose C minor at ARP SETUP F (KEY). Set HARM CHORD on NOTE SETUP F.
3. Program DEG 1, 4 and 5 with CHRD TRI: Cm, Fm and Gm.
4. On T2, set RFOL to T1. Start with FIXED OCT 3, UPDT TRIG and TRAN 0.
   Program a bass rhythm independently of T1; keep T2's arp off initially.
5. Change T1's KEY to D minor. The degree progression becomes Dm, Gm and Am;
   the bass follows the logical roots with its own rhythm.
6. Add another follower with its own HARM CHORD, SIZE and arp for a different
   arrangement of the same harmony.

Octaves use C0 = MIDI 0. Choose an appropriate octave for your synth.
A follower's TRAN is a semitone offset after its register choice. It does not
change the source, and intermediate followers do not accumulate offsets.

## A root is not the lowest sounding note

The logical root is chosen before inversion, spread and root omission.
A C chord can sound E–G–C while its followers still receive C. An arp can
walk every chord tone without making the bass walk after it. Same-tick source
trigs are captured before ordinary receiver output, including a higher-numbered
source track. An earlier microtimed receiver uses the previous root.

Follow TRIG changes pitch at the receiver's next note. LIVE can release and
retrigger a sounding sequenced voice when its source root changes; it restarts
the synth's envelope, preserves the scheduled release, and leaves rests silent.
It is not a pitch-bend glide. Root histories are temporary performance state.

## Play first, retain an editable sequence

HARM OFF uses native NOTE/NOT2–4. HARM NOTE plays a degree root; CHORD turns
it into the chosen quality. KEY changes preserve degree identity. Explicitly
turning HARM off resolves the degrees back into native NOTE; it does not
restore an older absolute-note sequence.

CHORD PLAY is selected with FUNC + UP/DOWN. The lower eight trig keys play
roots; upper keys select held chord variations. A variation press changes a
held chord immediately. Releasing it adds no notes; the next root uses the
latest still-held variation or the base CHRD. Live recording stores the root
and quality, not a flattened list of generated notes. Grid mode stays the
native sixteen-step editor. PAGE retains its native behavior.

SIZE, VOIC, SPRD and ROOT shape the outgoing chord without rewriting the root.
AUTO is a small deterministic search for nearby voicings, not a claim of
classical voice-leading correctness. Notes outside the MIDI range are omitted;
held notes keep the original pitch/channel identity needed to release them.

## Accumulate selected steps

With HARM NOTE or CHORD, NOTE MAIN E sets ACC: OFF or minus/plus 1 to 7
scale degrees. Hold a trig to override that step; an unlocked step inherits
the pattern/track default. OFF explicitly disables a step. There is no
separate zero/freeze value.

Each step starts unshifted and advances only when it actually sounds.
Rests, failed conditions and arp repeats do not advance it. Follow supplies
the root and register first; ACC shifts that root in degrees before native
semitone TRAN, scale correction and chord/arp output.

Press NOTE SETUP F to open HARMONY. UP/DOWN selects CHORD or ACCUM;
HARM OFF/NOTE/CHORD remains on the parent page. In ACCUM, A/B/C edit
LOW/HIGH/BOUND and D edits RESET, following their on-screen positions.
These are pattern/track settings, not step locks. See
[Harmony's controls](../../modules/midi-harmony/README.md) for boundary and reset policies.

## Scenes, Kits and saves

MIDI Scenes controls the normal MIDI main-page parameters through scene A/B.
With Harmony active, scene NOTE endpoints become degrees resolved through the
effective KEY. It does not turn HARM, CHRD, SIZE or voicing into scene controls.
Audio scenes continue alongside MIDI scenes on the same crossfader.

| State | Owner | Recall behavior |
|---|---|---|
| RFOL, register/response, KEY, HARM, DEG/CHRD defaults and voicing | Native Part | Part and Kit recall supply incoming defaults |
| Explicit DEG/CHRD step locks | Pattern, with Harmony companion files | Stay attached to the sequence across Kit changes |
| ACC default, limits, boundary/reset policy and step overrides | Pattern/track, with Harmony companion files | Copy/paste/undo and project save/reload; not Part or Kit settings |
| MIDI scene locks | MIDI SCENES tables; also saved in Kits | Recall the selected Part/Kit's scene configuration |
| Roots, accumulator offsets, AUTO history and held-note ownership | Runtime | Never saved as project settings |

Save a Kit for a reusable setup and save the project for its patterns and
companion files. Keep the complete project directory when copying it. A Kit
refers to the project's sample slots; it does not bundle sample files.

## Integration conventions

[MIDI Part State](../../modules/midi-part-state/README.md) owns shared native
Part boundaries. Readers see complete outgoing settings during a copy and
complete incoming settings afterward. UI edits target the selected Part;
playback uses the Part actually playing on each track. Small ROM entry gates
remain valid before the DRAM runtime is loaded. Initialization is explicit;
zero-filled BSS is not assumed on hardware.

Harmony registers as a [STORE](../../modules/store/README.md) client. Native
bank writes, companion writes and failures pass through shared callbacks.
The [Harmony/PLOCKS bridge](../../modules/harmony-plocks/README.md) owns only
the editing/copy hooks both modules need. KITS and MIDI SCENES implementations
are kept upstream's; adapters live with their consumer.

[MEMORY](../../modules/memory/README.md) sizes the volatile DRAM reserve from
linked code, data and BSS. These MIDI modules use those linked allocations;
they do not take pages from the live sample allocator. This DRAM reserve is
separate from the retained SRAM pool below and does not survive power-off.

Harmony always uses [MIDI SRAM](../../modules/midi-sram/README.md) fields
30/31 of each MIDI step, retaining all 8,192 Harmony/ACC step records in
their own pattern/track lanes. It leaves upstream's 4,768 PLOCKS P2 locks
and 16,384 MIDI Scenes bytes available. Audio sample locks remain native.
There is no alternate Harmony retention setting.

## Evidence and remaining work

Linked ColdFire tests check musical rules, graph bounds, ownership, codecs and
interleaved publication. Full firmware tests operate panel controls and capture
MIDI while changing Parts, Kits, Scenes and project state. Code identity, a
successful build and a clean resource ledger are separate from those tests.

Each remix and upstream rebase needs its own checks; a result from a different
selection is not integration evidence. Physical MIDI timing, battery retention,
interrupted checkpoints and long rehearsals remain hardware acceptance.
Emulator boot-stage traces cannot reproduce every cache or electrical startup
failure and are not evidence that a reported hardware logo hang is fixed.
