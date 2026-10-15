# MIDI module integration

The experimental `harmony-track-bus` selection adds MIDI Scales, MIDI Follow,
MIDI Harmony and MIDI Loopback to the existing Octabam bus. It includes the
Part, retained-memory and shared-hook integration those features require.
It adds no synths or ARP templates.

- Scales extends KEY in MIDI ARP SETUP to seven modes in twelve keys.
- Follow lets a MIDI track follow another track’s root/register.
- Harmony adds degree roots, chords and Chord Play using the native KEY.
- Loopback chooses EXT, INT or BOTH per Part, including Scenes and USB routing.

Read [the controls](../guide/MIDI_MODULES.md) and the
[exact remix boundaries](../../remixes/harmony-track-bus/README.md) before use.
Harmony selects MIDI TRACK retention and retains upstream PLOCKS and Scenes
capacity. Software validation does not establish physical power-off recovery,
device MIDI timing or hardware audio. No firmware is distributed.

The original upstream selections remain available. The separate Scales review
branch is the first module-sized author-adapter contribution; the full
integration is used for combined acceptance, not one giant upstream PR.
