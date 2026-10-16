# MIDI Part state test remix

Stock effects plus the shared native Part access and publication boundary.
This isolates the support module from Follow, Harmony, DEG and KITS. Run
`make check REMIX=midi-part-state`. Full project/Kit lifecycle and hardware
acceptance remain separate integration tests.
