# MIDI Loopback with Follow and Harmony

Focused composition of the CHAN routing window, RFOL and HARM windows and
shared native Part settings, over stock effects. No hardware validation.

Run `make check-remix REMIX=midi-loopback-follow`, then the Loopback panel
and native-Part verifiers with a copied project. Run `verify_midi_loopback_producers_port.py midi-loopback-follow --project
/path/to/source-project` for physical live Harmony/chord-arp routing. The
image gate also exercises Follow LIVE retriggers through all destinations.
