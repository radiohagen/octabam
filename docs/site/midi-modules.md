# MIDI module integration

The experimental `harmony-track-bus` selection adds MIDI Scales, MIDI Follow,
MIDI Harmony and MIDI Loopback to the existing Octabam bus. It includes the
Part, retained-memory and shared-hook integration those features require.
It adds no synths or ARP templates.

- Scales extends KEY in MIDI ARP SETUP to seven modes in twelve keys.
- Follow lets a MIDI track follow another track’s root/register, with FIXED,
  GRAV and SOURCE register modes and independent range controls.
- Harmony adds degree roots, chords and Chord Play using the native KEY.
  NOTE MAIN E sets ACC in scale degrees, with independent step overrides;
  press NOTE SETUP F for the CHORD and ACCUM settings sections.
- Loopback chooses EXT, INT or BOTH per Part, including Scenes and USB routing.

Read [the controls](https://github.com/radiohagen/octabam/blob/codex/integrate/midi/docs/guide/MIDI_MODULES.md) and the
[exact remix boundaries](https://github.com/radiohagen/octabam/blob/codex/integrate/midi/remixes/harmony-track-bus/README.md) before use.
Harmony always uses its own MIDI-step retention and retains upstream PLOCKS and Scenes
capacity. Software validation does not establish physical power-off recovery,
device MIDI timing or hardware audio. No firmware is distributed.

The current package selection follows upstream `octabam-bus`, including the
combined USB module and ATA write guard. Its author-source snapshot also
includes Loopback's native MIDI Part playback context and resident startup
activation. The source receipt pins both repositories; check the release
receipt for the image hash and completed tests.

The original upstream selections remain available. The separate Scales review
branch is the first module-sized author-adapter contribution; the full
integration is used for combined acceptance, not one giant upstream PR.
