# USB: one module, configured in BRAIN

## 1. What it is

The four USB modules (USB MIDI, USB AUDIO OUT, USB AUDIO IN, USB
CROSSBAR) become one module, `USB`, whose LAYOUT and INPUTS settings are
held by the brain at run time: edited in SETTINGS, read at boot, effective
at the next enumeration. LAYOUT and INPUTS each gain OFF, so the one module
expresses every selection the four expressed, MIDI-only and out-only
included. The store id is new: `octabam.usb` (records under the two
current ids stop applying; section 6).

Decisions (Sam Banks, 14 Oct 2026):

- both settings run time (`Apply.NEXT_BOOT`);
- USB CROSSBAR merges in;
- OFF values;
- new store id.

## 2. Where it starts

| module | kind | proof | settings | detours | notes |
|---|---|---|---|---|---|
| USB MIDI | CF_PATCH | HARDWARE (Sam's MKII, image 64, 25 Sep 2026; Tim's MKI OCTATRICK9, 26 Sep; Kazeko's MKI #633, 6 Oct; Ignorato's MKII OCTABAM21, 9 Oct) | none | 9, incl. ISR `0x4001e606`, reset `0x4001e91c`, sessend `0x4001e952` | `usbmidi` linked verbatim (1,124 B at `0x400d24f0`, sha `6291d91e…`); gates `verify_usbmidi_rx`/`_clock`/`_replug` |
| USB AUDIO OUT | CF_PATCH | PORT (`verify_usb`); ran on units (Sam image 64, Tim OCTATRICK9, Bryan T build 16, @clickysteve P3, Ignorato OCTABAM21) | LAYOUT, `Apply.BUILD`, six layouts | 8; **overrides** USB MIDI's three sites | poke (composite device class); gates `verify_usb` + per-layout `verify_usb_align`/`verify_usb_post` |
| USB AUDIO IN | HYBRID | PORT (`verify_usb_in`); ABCD ran (Bryan T, usbin-test build 16, 27 Sep 2026) | INPUTS, `Apply.BUILD`, AB/CD/ABCD | 3 CF + DspHook P:$88 + payload-A DspSection | SRAM claims sized by INPUTS; `requires=("USB MIDI", "USB CROSSBAR")` |
| USB CROSSBAR | CF_PATCH | HARDWARE (Bryan T, usbin-test builds 12–16) | none | 1 (`0x4001e030`) | no claims |

Phase 1 of the store (6 Oct 2026, `27ee5b1e`): the eight layout modules
became OUT + IN with `Module.variant`/`bind`; `make identity`: 25 images
byte-identical. BRAIN.md's to-find-out list names this merge as the next
step.

## 3. The merged module

- `modules/usb/`, key `USB`, `Kind.HYBRID`, `Category.MIDI_USB`,
  `Proof.PORT` (the floor; `proof_note` carries the hardware runs, as
  USB AUDIO OUT does today), `Store("octabam.usb")`.
- Unit names keep (`usbmidi`, `usbmidi_rx`, `usbmidi_clamp`, `usbmidi_cfg`,
  `usbaudio`, `usbaudio_in`, `usbcrossbar`): BRAIN's PERFORMANCE hooks name
  `usbaudio_underruns`, `usbaudio_overruns`, `in_counters`,
  `usbmidi_tx_drops`, and the verbatim `usbmidi` reference stays.
- Detours: one per site. The three `Override`s go: the units already chain
  by symbol (`usbaudio.s` calls `usbmidi_rx_bus_end`). Ledger rule
  unchanged: two detours at one site refuse, same module or not.
- Claims: USB AUDIO IN's SRAM at the ABCD maximum (`0x80007c00` dTDs
  `0x80`; `0x80007c80` packet buffers `0x300`; `0x80007f80` vendor reply
  `0x40`) ✅.
- Descriptors: `descriptors.py` moves beside the merged sources; its audio
  and IN additions become internal to the module (today they key on module
  presence).
- The manifest's one `author` field carries the primary author
  (markandrus/octemu); the per-part credits stay in `proof_note` and the
  README, as OUT credits its POST layout today. THIRD_PARTY.md and the
  README.md module table (rendered by `tools/remix/index.py --write`)
  update with the merge.
- `brain.lock`: new file, new store. The released LAYOUT and INPUTS labels
  carry over with OFF appended; append-only from then on.

## 4. Settings

| setting | kind | labels | default | apply | scope | early |
|---|---|---|---|---|---|---|
| LAYOUT (key 1) | Option | OFF, TRACKS MAIN CUE, TRACKS, MASTER, MAIN CUE, MAIN, TRACKS POST | open (today's manifest default: TRACKS MAIN CUE) | NEXT_BOOT | CARD | yes |
| INPUTS (key 2) | Option | OFF, AB, CD, ABCD | open (today's: AB) | NEXT_BOOT | CARD | yes |

- NEXT_BOOT, not LIVE: the host reads descriptors only at enumeration, and
  the firmware has no software reset trigger — a change applies at the next
  boot or replug.
- The boot read must precede enumeration. If the card mounts first, the
  value comes from `card.work`; if not, from the CS1 early block
  (`Setting.early`, BRAIN.md section 6.4) — the order is an open item
  (section 9), and the CS1 block is not built (BRAIN.md section 12).
- The official remixes give layer-2 values, not Pins: LAYOUT MAIN CUE,
  INPUTS OFF (the unit stays changeable).
- The value table and `read_macro` exist (BRAIN.md section 5); USB would
  be the first non-BRAIN consumer of run-time settings. The SETTINGS list
  itself is port-proven only (BRAIN.md section 12).

## 5. The run-time code

### 5.1 Producers (LAYOUT)

All six producers assemble into the DRAM arena reserve (1,707 pages /
10.5 MB in every DRAM remix, PLACEMENT.md). `usbaudio.s` is 1,959 lines
with 18 `USB_LAYOUT`-guarded blocks; the all-six unit is 🟡 low tens of KB,
measured at build. The frame shim `0x4000d9a0` dispatches on the boot-read
value; OFF runs no producer. Falsifier: the all-six unit no longer fits the
reserve.

### 5.2 Inject (INPUTS)

One parametric inject in payload A: the width (2 or 4) is a word the
ColdFire already writes per frame, beside the open flag at working bank
+$320 (`usbaudio_in.s` `in_build`) — no new ColdFire→DSP route; the one
BRAIN.md section 5.3 leaves unchosen is not needed here. The frame
transfer builds 96 (pair) or 160 (four) halfwords by the boot value. The
inject must fit the donor region `rx_inject_abcd` fits today ✅; the
parametric form is 🟡 similar length. Falsifier: a form with no stock
payload-A site (TRAPS.md).

### 5.3 Descriptors

Channel counts and maxpkt are baked into `cfg_fs/hs/os_fs/os_hs` today.
Run-time values mean all variant sets are carried, padded to one length so
the single `cfg_len` clamp survives (`configs()` already pads FS to HS
length ✅). The responder's four `pea <table>` operands (symbol refs
`0x4001d882/8a/c0/c8`) become a selector reading the two boot values; the
clamp sites `0x4001d858/0x4001d896` stay. Sizes today ✅: MSC-only 32 B,
+MIDI 124, +OUT 250 (HS); HS maxpkt per layout: TRACKS MAIN CUE
12×80 = 960 B, TRACKS 768, TRACKS POST 768, MAIN CUE 192, MASTER 96,
MAIN 96; IN's EP3 OUT 12×2×4 = 96 or 12×4×4 = 192. All sets together are
🟡 under 8 KB of DRAM, measured at build.

### 5.4 Invalid combinations

INPUTS ≠ OFF with LAYOUT = OFF cannot be served: interface 5's implicit
feedback is EP3 IN, which needs an output layout (the build asserts the
same ✅). The edit rule is open: SETTINGS refuses the pair, or the
responder serves MIDI-only descriptors until fixed.

## 6. Remixes and cards

- 33 remixes select USB MIDI; 14 of them also select IN/CROSSBAR. Each
  `remix.py` drops the four keys for `USB`; `settings` entries re-key to
  `("octabam.usb", "LAYOUT"/"INPUTS")`; Pins become layer-2 values.
- Records under `octabam.usb-audio-out` / `octabam.usb-audio-in` on
  users' cards: unknown-but-kept on write, stop applying (BRAIN.md
  section 7.7). Accepted with the decision.
- `make identity` cannot be the proof past phase 1 (section 8): every image
  changes by design. The gates (section 7) and `make reach RUN=1 KEEP=1`
  are the floor.

## 7. Gates

- All current gates move into the one module: `verify_usbmidi_rx`,
  `verify_usbmidi_clock`, `verify_usbmidi_replug`, `verify_usb`,
  `verify_usb_in`, `verify_usb_align` (TRACKS MAIN CUE), `verify_usb_post`
  (TRACKS POST).
- NEXT_BOOT values are read at boot, so covering six layouts needs six
  boots; the port re-boots per value in one gate run. `verify_brain` shows
  the port can drive settings (panel gestures write `card.work` ✅).
- Fixed here: `verify_usb.py:83` imports
  `modules/usb-audio-out-tracks-post/manifest.py`, removed 6 Oct 2026 — a
  fresh run on a TRACKS POST image crashes 📖 (cached passes mask it).
- New gates: the descriptor selector serves each set for its values; the
  parametric inject writes the right slots for 2 and 4; the producer
  dispatch runs the six layouts and OFF.
- Hardware round: the whole run-time SETTINGS increment is pre-hardware
  (BRAIN.md section 12); the merged module's README records the unit runs.

## 8. Phases

| phase | content | proof |
|---|---|---|
| 1 | the mechanical merge: one manifest, store `octabam.usb`, remix layer-2 values, gates re-keyed, settings still `Apply.BUILD` | `make identity` (images byte-identical, as store phase 1) |
| 2 | run-time LAYOUT: all six producers + dispatch + gate | `verify_usb` × six values |
| 3 | run-time INPUTS: parametric inject + width word + ABCD-max claims + gate | `verify_usb_in` × three values |
| 4 | descriptor sets + responder selector + the edit rule | the new descriptor gate |
| 5 | `make reach RUN=1 KEEP=1`, the remix READMEs, the hardware round | reach + units |

## 9. To find out

| item | instrument |
|---|---|
| card-mount vs USB-enumeration order at boot | port |
| the CS1 early block (unbuilt; BRAIN.md section 12) | build, then port |
| all-six producer size in the reserve; per-frame dispatch cost | build, port |
| parametric inject cycles | port (cycles gate) |
| re-enumeration after replug with a changed value, per OS | units |
| INPUTS default; the invalid-combination edit rule | decision |
