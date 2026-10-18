# MIDI Loopback Translation

Isolated follow-up: Loopback, Part State and STORE with optional final-note
translation. No DSP effects are replaced. Official remix selections are unchanged.

Translation defaults OFF. Open MIDI NOTE SETUP, select CHAN and press A for
ROUTING. A selects DEST; B selects RE-MAP independently. C/D select
source/target references, E the symmetric ± range; F is unused. Initial values are
C4 (60) → 84, range ±12 (72–96). OFF keeps the normal controls visible and ignores
their encoder turns while retaining the values. Reference pitch is manual; save the project before
power-off to preserve these separate settings.

See [configuration and storage](../../../docs/site/usage/midi-loopback.md#optional-note-translation).

Software/emulator verification is separate from hardware acceptance. This
follow-up has not been tested on physical hardware.
