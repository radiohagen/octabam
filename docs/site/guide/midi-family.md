# Personal MIDI remix family

MIDI Core, MIDI Bus and MIDI Inserts extend their corresponding upstream
remixes without removing effects or changing defaults. All include Scales,
Follow, HARM, Loopback, Part State/SRAM and RLEN PLEN. Core keeps the fourteen
stock effects; Bus keeps SEND and its delay/reverb servers; Inserts keeps
TRANSIENT and EUCLID alongside the upstream stations and effects.

HARM edits held MIDI trigs; PLOCKS P2 edits held audio trigs. Their common
EDIT EVENTS dispatcher also preserves native clipboard/undo operations.
SEQUENCER EVENTS shares transport and accepted MIDI notifications between
HARM, Follow and, on Inserts, EUCLID. Loopback/Scenes is a separate routing
adapter and preserves EXT, INT and BOTH destinations for scene CC output.

Build with `make image REMIX=midi-core BUILD=93` (or `midi-bus` / `midi-inserts`).
The private package contains complete flashable BIN and switchable RMX images,
source identities, module selections, checksums and software evidence. Firmware
contains proprietary OS bytes and stays outside Git. No hardware validation is
implied. With Brain already installed, copy the RMX files to `/BRAIN/REMIXES/`,
safely eject before leaving USB Disk Mode, then use Brain's Remix Switch.
Start with a new project when moving between different effect layouts.
