# MIDI Loopback and USB MIDI test remix

Stock effects with [MIDI Loopback](../../../modules/midi-loopback/README.md)
and [USB-MIDI](https://github.com/radiohagen/octabam/blob/codex/integrate/midi/modules/usb-midi/README.md). Producer-side routing
runs before the shared sender: INT bypasses both DIN and USB; BOTH reaches
the unchanged USB entry mirror and DIN sender once.

Development fixture only; all tracks default to EXT, with CHAN-press routing and native Part storage.
Build with `make bus REMIX=midi-loopback-usb`, then run
`REMIX=midi-loopback-usb python3 tools/verify/verify_usb.py` and
`.venv/bin/python tools/verify/verify_midi_loopback.py midi-loopback-usb`.
The project gate also accepts `--project /path/to/source-project`.
Add `--controls` to test filter CC locks, MIDI LFO and live CC knobs.
Add `--routing` for eight simultaneous tracks with mixed destinations.
The machine gate checks the USB accumulator as well as DIN output for all
track/channel/route combinations and both panel CC branches. USB enumeration,
RX/TX and the RTOS scenarios are separate proofs; no concurrent USB load,
hardware use or USB timing proof is claimed. Receipts stay under
`out/midi-loopback-usb/`.
