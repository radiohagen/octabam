# Build and Flash

Use this procedure to build a card image from your own copy of Octatrack OS
1.40C, then install it on the unit. For Linux and WSL2 setup, see the
[detailed build guide](https://github.com/sambanks/octabam/blob/main/docs/guide/BUILDING.md).

!!! warning "Read before flashing"
    octabam is community software, not supported by Elektron. A failed flash
    can leave the unit unable to boot until stock OS is reinstalled. Keep a
    working Startup Menu, DIN MIDI interface, and stock OS 1.40C available.
    Follow [Safety and recovery](safety.md) before proceeding.

    Do not share a built image. A `.bin` or `.syx` contains Elektron's OS.

## 1. Prepare the Computer

You need:

- macOS with Xcode Command Line Tools and Homebrew, or Linux / WSL2 (not
  native Windows).
- Python 3.10 or newer, CMake, and `uv`.
- An Octatrack MKI or MKII running OS 1.40C. octabam's own effects have
  been tested on an MKII.
- A CompactFlash card for the card-flash procedure. For MIDI flashing or
  recovery, use a 5-pin DIN MIDI interface connected to MIDI IN and a SysEx
  sender. The Octatrack USB port cannot install an OS upgrade.
- Stable power. Do not move or disconnect the unit during a flash.

On macOS, install the command line tools and dependencies:

```bash
xcode-select --install
brew install cmake uv
```

Then clone and prepare the project:

```bash
git clone --recurse-submodules https://github.com/sambanks/octabam
cd octabam
make setup
make emu-setup
make os
make recon
```

`make os` downloads stock OS 1.40C from Elektron and prints its SHA256.
`make recon` unpacks it for the image builder. If you cloned without
`--recurse-submodules`, run `git submodule update --init` before continuing.

## 2. Build and Check the Image

Choose one of the [official remixes](choosing.md), then build it. Replace
`octabam-bus` with your chosen remix name. Pick a new build tag each time you
flash; the tag appears in the unit's OS version. Use one or two characters:
for example `1`, `91`, or `A0` (after `99`).

```bash
make image REMIX=octabam-bus BUILD=91
```

The build creates:

| File | Use |
|---|---|
| `out/OCTATRACK_OCTABAM91.bin` | Flash from the CF card. |
| `out/OCTATRACK_OS1.40C_OCTABAM91.syx` | Flash over DIN MIDI or use for recovery. |

Run the remix checks before flashing:

```bash
make check REMIX=octabam-bus
```

This builds the image, runs its gates, and boots it under the local
emulator. It is the minimum project check; it does not establish that the
image works on hardware. See the selected remix page for its test status and
any required track or project setup.

## 3. Back Up the Card

Use USB DISK MODE to copy the full CF card to your computer. An OS upgrade
does not format or replace the card. Remixes with KITS write `kits.work`
into each project they load; stock OS ignores this file and continues to
use the saved Parts.

## 4. Install the Image

Choose one of the following methods.

### From the CF Card

Use this method when the Octatrack boots normally:

1. On the unit, select **PROJECT → SYSTEM → USB DISK MODE → YES**.
2. Copy the `.bin` file to the root of the mounted CF card, not into a
   folder.
3. Eject the card from the computer, then leave USB DISK MODE on the unit.
   This ensures the copy has finished writing.
4. Select **PROJECT → SYSTEM → OS UPGRADE → YES**, then confirm.
5. Wait for the unit to finish and restart. Power-cycle it once more before
   testing; an OS upgrade does not clear DSP RAM.

### Over DIN MIDI

Use this method if the unit cannot boot far enough to use USB DISK MODE, or
if you prefer a DIN MIDI transfer:

1. Connect the MIDI interface's **MIDI OUT** to the Octatrack's **MIDI IN**.
2. Power off. Hold **FUNC** while powering on to open the STARTUP MENU.
3. Press **TRIG 3** for MIDI UPGRADE and wait for “READY TO RECEIVE MIDI
   UPGRADE”.
4. Send the `.syx` file with a SysEx app, or run
   `make midi-flash PORT=<port> SYX=<file.syx>`. Do not merge other MIDI
   data or clock into the upgrade port. If the unit reports a checksum
   error, re-enter the Startup Menu and resend at a slower rate.
5. Wait through PREPARING FLASH and UPDATING FLASH. Do not power off or
   disconnect the cable during either phase.
6. Let the unit finish booting, then power-cycle once more.

## 5. Confirm the Installation

Open **SYSTEM STATUS → OS VERSION** or check the boot screen. It should
show the tag you chose, for example `OCTABAM91`. If it shows `1.40C`, the
stock OS is still installed.

Some remixes change effect parameter layouts or default track assignments.
For projects created before installation, follow the project preparation
steps on the relevant [remix page](choosing.md). A project created on the
unit after installation does not need those steps.

## Restore Stock OS

If the modified OS will not boot, use the recovery procedure in
[Safety and recovery](safety.md). If the unit boots, you can also install
Elektron's stock `.bin` from the CF card with the same steps above.

For detailed platform setup or troubleshooting, see the
[full build guide](https://github.com/sambanks/octabam/blob/main/docs/guide/BUILDING.md).
