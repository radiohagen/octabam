# MIDI Loopback

Internal routing of MIDI-track sequenced and live notes, CCs, pitch bend,
channel pressure and Part bank/program changes through the normal MIDI receiver. All eight source
tracks and output channels 1–16 are supported at these producer boundaries.
The receiver's channel assignments, CC/note receive switches and note maps
still decide which audio controls respond. The routing window does not block
native received-MIDI track-selection commands.

## On the Octatrack

On a MIDI track, open **NOTE SETUP** with **FUNC + SRC**. Turn **A: CHAN**
to choose its output channel, then **press A**. The press applies the pending
channel exactly as before and opens **ROUTING** for that track.

Turn **A: DEST** in the window:

| DEST | Track output |
|---|---|
| EXT | Existing DIN/USB output only; default. |
| INT | Internal delivery; bypass the shared DIN/USB sender. |
| BOTH | One internal copy plus existing DIN/USB output. |

Edits apply immediately. A press, YES or NO closes the window. Track/page
keys close it first; a second press changes selection. B–F are inactive;
transport and chromatic keys pass through. CHAN shows an **I** suffix for INT
or **B** for BOTH (for example `2I`); EXT keeps the normal channel display.
CHAN OFF still disables sequencer output.

DEST belongs to each MIDI track in each native Part. Part Save/Reload/Clear,
copy/paste and project save/load use the existing native storage. Playback
reads each track's playing Part, independently of the Part selected for editing.
Fresh Parts use EXT. No parameter locks or separate settings file are added.
The shared `MIDI PART STATE` module is required; KITS is optional.

Changing the playing destination releases held notes at their original
channel/destinations. Part replacement also releases the outgoing ownership;
late stock releases are consumed without sending a second note-off. A channel
change is observed at the next sequencer boundary, or immediately after the
CHAN press. Other tracks' notes remain owned by their original tracks.

For example, M1 on channel 1 with INT and CC1 assigned to CC 34 can sequence
T1 FILTER BASE, provided T1 receives channel 1 and audio CC reception is on.
M2 can remain EXT for an external synth. Stock arbitration between tracks
sharing a channel, pitch or CC still happens before these hooks; routes do
not create independent copies of the stock note pool or CC cache.

## Boundaries

The destination covers sequencer and arp output, live trig keys and preview,
CC locks/LFOs and panel controls, pitch bend, channel pressure, Part
BANK/SBNK/PROG, Harmony live chords, Follow LIVE retriggers and STOP's
CC123 panic. Held releases retain their original destinations. Two-byte
pressure/program packets and paired bank messages retain their wire lengths.

Clock, transport, song position, SysEx and the project-wide program-change
sync sender are global rather than MIDI-track output; their behavior stays
unchanged. Received-MIDI forwarding, CC Direct Connect and audio-knob
feedback are input/feedback paths, not new internally copied track events.
The generic received-parameter setter remains excluded to prevent recirculation.
For internal packets, the receiver uses a private channel map containing audio
listeners and audio-mode auto-channel only. MIDI-track forwarding/recording is
excluded, so internal packets cannot escape through input echo or feed back
through Harmony/Follow. Normal DIN/USB input retains the native channel map.

Use dedicated channels/pitches without overlapping external held notes.
Stock's incoming-note bookkeeping is shared by channel and pitch; receiver
ownership across independent external and internal senders is not separated.
Changing audio receive assignments while notes are held and cross-project
transitions during playback remain unproved. Audio locks/scenes and dense
simultaneous external traffic still need separate integration tests.

## Implementation

Four ColdFire DRAM units, no DSP effect slot. SETUP offset 12 is owned by
MIDI PART STATE: Follow uses bits 0–1 and DEST uses bits 2–3. Writers preserve
each other. DEST 3 or invalid flags decode as EXT. `lb_routes[8]` is an applied
runtime cache; tools must use `lb_dest_write(track, route)` to edit native
settings. `lb_set_route` remains the low-level cache/cleanup helper.

Boundaries:

| Boundary | Purpose |
|---|---|
| Pinned sender operands in track producers and cleanup routines | Route complete channel messages before `midi_send` at `0x40010bc8`, leaving USB-MIDI's entry hook intact. |
| `0x4009f794` | Synchronize native Part destinations and effective output channels at sequencer entry. |
| `0x40005558` | Alternate native and internal messages in the MIDI task, then use the installed dispatch table and handlers. |
| `0x4009f26e` and cached live sender operands | Capture live CC/bend/pressure before the tail restores source track. |
| `0x4009ecb4` | Part setup sender: track in `a3`, bank/Part from its arguments. |
| `0x4009ea68`, `0x4009ea96`, `0x4009eb50` | Live notes: source track in `d5`, UI Part destination. |
| `0x4009f288` | STOP panic combines routes of tracks assigned to each channel. |

The live branches retain track identity in `d7` and qualify the parent
return address `0x4005542c`. Trig preview (`0x40043b0e`) also qualifies. The generic received-MIDI setter
(`0x40054f74`) is excluded without a global origin flag. The MIDI LFO engine
writes the modulated parameter array used by the two sequencer CC producers.
All patched operands and displaced instructions are pinned in the manifest.

The byte parser is untouched. A 256-entry ring holds complete messages.
The consumer copies each message to a stable slot before releasing capacity.
One coalesced wake token uses the native MIDI queue; a full native queue does
not receive an extra token. Internal and native messages alternate while both
are available. The wake token never reaches the MIDI handler table.

The ownership table covers all 2,048 channel/pitch pairs, storing source track
and the destinations used at note-on. New internal note-ons/controllers stop at 127
pending messages; at most 128 internally held pitches reserve 128 release
slots across all channels. An INT admission failure leaves a tombstone so
its later release does not leak externally; BOTH still sends the event
externally. Counters expose accepted/delivered messages, drops and high water.
Cleanup scans a bounded ownership table with interrupts masked and uses the
stock sender for external releases. Its worst-case hardware cost and UART
backpressure are not yet measured.

The platform reserve takes approximately 10 MB of sample memory when added
to an otherwise stock image. The module's linked code/state uses only a
small portion of that existing reserve; consult the build layout for size.

## Verification

Original prototype baseline, 8 October 2026: `make check REMIX=midi-loopback` and
`make check-remix REMIX=midi-loopback-usb` passed all runnable checks,
including USB enumeration, RX/TX and clock gates. The generic `verify_set`
was skipped without `OT_PROJECT`. Explicit loopback fixtures separately
passed eight note/lifecycle scenarios, twelve control scenarios and one
simultaneous eight-track scenario on each build. Each build's three receipt
groups name the same image hash. No hardware validation is claimed.

The gate executes the built runtime, patched operands and stock sender,
queue routines and receive handlers. It covers:

- M1–M8 × channels 1–16 × EXT/INT/BOTH, with exact delivery and DIN counts.
- USB accumulator contents and INT suppression when USB-MIDI is composed.
- Both live CC branches, CC1–CC10, all-track routing and input-origin exclusion.
- Every route transition, channel changes/OFF, old-destination cleanup,
  another track remaining held, and late stock release suppression.
- Queue fairness, native-queue saturation, ring wrap, release reserve,
  the cross-channel held-note cap and overflow recovery.

The disposable project scenarios run the real sequencer, RTOS, MIDI dispatch
and UART receiver. EXT, BOTH, INT, UART reference, route change while held,
channel change, CHAN OFF and STOP are compared using receiver state and wire
captures. T1 level reaches 70; held-note bookkeeping returns to zero. INT
produces the same receiver result without the fixture's external MIDI.
Channel edits in this gate poke the current Part and effective channel bytes;
they do not constitute panel-menu interaction proof.

A separate `--routing` scenario runs eight simultaneous tracks with mixed
EXT/INT/BOTH destinations, checking each wire stream and audio track level.

The filter-control fixture uses CC 34, locks 32 then 96, and TRI LFO1 with
SPD 32, MULT x16, DEP 24, FREE. Its panel encoder call changes CC1 from 64
to 80. The gate compares every incoming filter write with the outgoing CC
values. INT repeats the same receiver writes with no external messages.
Audio CC receive OFF and incoming auto-channel CC with Direct Connect
OFF/ON are separate cases. The panel test calls the stock encoder routine;
it does not simulate a physical encoder.

```sh
make check REMIX=midi-loopback
.venv/bin/python tools/verify/verify_midi_loopback.py --project /path/to/source-project
.venv/bin/python tools/verify/verify_midi_loopback.py --controls --project /path/to/source-project
.venv/bin/python tools/verify/verify_midi_loopback.py --routing --project /path/to/source-project
make bus REMIX=midi-loopback-usb
.venv/bin/python tools/verify/verify_midi_loopback.py midi-loopback-usb --project /path/to/source-project
REMIX=midi-loopback-usb python3 tools/verify/verify_usb.py
```

Source projects are only read; fixtures, receipts and captures stay under
`out/<remix>/`. `--controls --control-kind locks|lfo|knob` selects one group.
These gates prove ColdFire control state, not rendered audio, electrical
MIDI timing, concurrent USB load or hardware reliability. The generic
project/audio gate requires its own `OT_PROJECT` fixture.

## Producer regression checks

`verify_midi_loopback_producers.py` runs real live-note, live bend/pressure,
and Part setup routines for all eight tracks and all three destinations. It
checks both live branches, bank pairs, two-byte packets, panic, old-destination
releases, USB suppression and installed frame-control operands. When composed,
it also runs Follow LIVE retriggers and Harmony's owned live voices.

`verify_midi_loopback_producers_port.py <remix> --project <source>` runs
physical chromatic key events with Harmony chords and arp through the full
firmware and MIDI task. EXT/BOTH wire notes match; INT has no external notes;
internal messages drain and held counts return to zero. Hardware timing and
physical MIDI capture remain separate acceptance work.


## Eight-producer overload gate

`tools/verify/verify_midi_loopback_stress.py` executes 48 seeded floods:
eight tracks hold the full 128 internal voices, a stalled receiver admits
127 CCs and sheds 897 excess CCs, then all 128 releases must fit (255 slots).
Alternate rounds change all routes while held and deliver late stock offs.
The gate checks exact FIFO bytes, no phantom releases for rejected notes,
ring wrap, recovery, and all 18,384 admitted messages delivered with no held
notes left. A separately full 256-entry native receive queue checks alternating
service and wake recovery. Run on both Loopback and Loopback+USB images.
These are linked-code/stock-queue results; physical DIN/USB scheduling and
hardware latency are not established by this test.

## Routing-window verification

`verify_midi_loopback_settings.py` executes the native Part getters/writers,
all tracks/Parts at the first/last bank, invalid values, current-bank mirrors,
playing-context separation, Part replacement cleanup and CHAN formatting.
With Follow selected it also checks reciprocal preservation of MODE/UPDT/DEST.
`verify_midi_loopback_ui_port.py --project DIR` drives panel key/encoder events,
checks CHAN activation and window closing, captures the LCD, saves the native
project, reloads disk and retained memory, and checks fresh-project EXT.
Receipts and screenshots live under `out/<remix>-ui-port/`.
These are emulator checks, not physical-device playback or timing acceptance.

Validated 12 October 2026: `make check REMIX=midi-loopback` passed;
`make check-remix REMIX=midi-loopback-usb` passed 9 image gates and
`make check-remix REMIX=midi-loopback-follow` passed 32. The combined image
also passed the panel/persistence verifier, native Part Save/Reload/Clear/Paste,
and 21 full-firmware note/control/eight-track scenarios. Generic project/audio,
reserve-write and concert project checks were skipped without `OT_PROJECT`;
the targeted virtual-card checks used an explicit copied source project.
No hardware playback or timing validation is claimed.
