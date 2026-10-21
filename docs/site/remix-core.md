# Octabam Core

This revision uses the shared EDIT EVENTS platform for page-two locks. Software validation does not establish hardware acceptance for this revision.


![BRAIN in the main menu, added by Octabam Core](img/brain/pane.png)

*BRAIN in the main menu, added by Octabam Core*

Octabam Core adds the core features to Octatrack OS 1.40C. All 14 stock
effects and both effect menus stay as stock has them, with stock LO-FI's AMF
knob fixed (the LOFI AMF FIX module). [Octabam Inserts](remix-inserts.md)
and [Octabam Bus](remix-bus.md) add effects to this set.

## Included features

- [BRAIN](brain.md): templates, settings, defaults, and remix switching.
- [KITS](reference/modules/kits.md): save and recall a Kit for each pattern.
- [Page 2 locks](reference/modules/plocks-p2.md) and
  [scene locks](reference/modules/scenes-p2.md): control both effect pages.
- [MIDI scenes](reference/modules/midi-scenes.md), CC mapping, and CC feedback.
- [USB](reference/modules/usb.md): MIDI input and output, plus audio to a computer: the 16 track channels, MAIN and CUE by default.
- Recorder, sequencing, mute, and storage fixes listed below.

## Build and install

[Build and Install](web-builder.md) builds this remix in the browser. To build
from source instead:

1. **Build.** Pick a build number; it becomes the OS version the unit shows.

   ```bash
   make image REMIX=octabam-core BUILD=91
   ```

2. **Back up the card.** KITS writes `kits.work` into each project it loads.
3. Follow [Build and Install](web-builder.md#install-the-image) to install the image and confirm
   that SYSTEM STATUS → OS VERSION reads `OCTABAM91`.
4. To restore stock OS, follow [Safety and recovery](safety.md).

If the unit misbehaves, the failure register lists what has gone wrong and
why: https://github.com/sambanks/octabam/blob/main/docs/contributing/FAILURE_MODES.md

## Module list

Every module in the image, credited to its author:

??? note "Full module list and authors"

    --8<-- "reference/_remix-octabam-core.md"

USB combines MIDI, audio output, audio input and the input crossbar in one
module. Its settings (TRACKS, MAIN, CUE, MASTER, MIDI) are changed on the
unit in PROJ > BRAIN > SETTINGS and take effect at the next boot; IN is fixed
at OFF in this remix. See [USB](reference/modules/usb.md).

## Memory use

| Resource | Stock OS | Octabam Core |
|---|---|---|
| Sample and recorder memory | 14,602 pages | 12,895 pages (platform reserve) |
| Free DSP words | — | 0. LOAD METER does not fit, so BRAIN has no LOAD view DSP rows. |

## Where it has run

The upstream baseline received cursory testing on an MKII (owner report,
16 Oct 2026). The shared-event revision has not run on hardware. Port gates:
`make check REMIX=octabam-core` and the reach round.
