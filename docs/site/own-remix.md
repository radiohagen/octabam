# Build Your Own Remix

You can assemble a personal remix from modules already in octabam. A remix
chooses which modules are included and which effects appear in the FX1 and
FX2 menus. The remixer shows compatibility conflicts and rebuilds the image
as you change the selection.

This guide is for combining existing modules. If you want to create a new
feature or contribute a module, start with the
[developer documentation](https://github.com/sambanks/octabam/blob/main/CONTRIBUTING.md)
and the [module author guide](https://github.com/sambanks/octabam/blob/main/docs/contributing/MODULES.md).

## 1. Prepare the Build Environment

Follow the [build guide](build-flash.md) through installing the toolchain and
preparing your own OS 1.40C. The interactive remixer also needs its optional
Python environment:

```bash
make emu-setup
```

See the [remixer guide](https://github.com/sambanks/octabam/blob/main/docs/guide/REMIXER.md)
for detailed setup notes, Linux and WSL2 audio, and the keyboard controls.

## 2. Select Modules and Effects

Start the interactive remixer:

```bash
make remix
```

Use the arrow keys to browse modules and effects. In the **Available** pane,
press `Enter` to add a module. In **Choosers**, arrange FX2 effects and press
`1` to add or remove an FX1 entry. The **Unit** pane describes the selected
module and its compatibility constraints. The remixer rebuilds and boots
the selection under the emulator as you edit. It does not flash the
Octatrack.

Press `l` to load a starting remix, or `s` to save your selection under a
new name. The selection is saved as `remixes/<name>/remix.py`.
For the full key reference and hand-editing options, see the
[remixer guide](https://github.com/sambanks/octabam/blob/main/docs/guide/REMIXER.md).

Select **USB** for USB MIDI and optional audio in either direction. Its
LAYOUT and INPUTS settings replace the four former USB module selections.
For now they are build settings, so a different USB channel selection needs
a rebuilt image; they cannot yet be changed on the unit.

## 3. Record and Check the Remix

Add `remixes/<name>/README.md` describing what the remix includes and what
has been tested. Update the remix index, then run:

```bash
make docs
make check REMIX=<name>
```

`make check` builds the image, runs its gates and boots it under the port.
It is the minimum check before flashing; a successful build alone does not
show that the remix works on hardware. For image creation and installation,
continue to [Build and flash](build-flash.md).

## Next Steps

- [Choose a ready-made remix](choosing.md) if you want a tested starting
  selection.
- [Developer documentation](https://github.com/sambanks/octabam/blob/main/CONTRIBUTING.md)
  and [writing a module](https://github.com/sambanks/octabam/blob/main/docs/contributing/MODULES.md)
  if you want to add a new feature or share a module.
