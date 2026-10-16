# MIDI Follow test remix

Stock effects plus [MIDI FOLLOW](../../../modules/midi-follow/README.md)
and MIDI PART STATE. No Harmony, extended Scales or Loopback is selected.
MIDI NOTE SETUP knob D adds **RFOL: OFF / T1–T8**, independently per track.
Followers keep their own rhythm and transposition. FIXED chooses an absolute
octave; SOURCE follows the source register with an octave offset. TRIG updates
at follower trigs; LIVE can also retrigger held follower notes on source changes.
Sources may play chords or arps. RFOL defaults OFF, and settings belong to the
native Part. There is no Scale Quantizer dependency.

Stock 1.40C preserves a valid RFOL source number but resets the register mode,
response and octave fields on loading. Saving that Part on stock loses those
settings. See the module's stock compatibility section before sharing projects
between firmwares.

Build/check: `make check REMIX=midi-follow`. The module README describes the
optional virtual-project/panel tests and limitations. These exercise firmware
under the emulator; hardware acceptance of the rebased image remains pending.
