# MEMORY

Platform module. Owns octabam's reserve in stock's audio page arena and sizes it per remix from what the remix's modules claim. Every remix with a DRAM unit carries it; the registry appends it. It has no code.

## The reserve

Stock keeps one arena of 6,144-byte pages for Flex samples and the track recorders: 14,602 pages at `0x40a955e0` (`tools/remix/arena.py`). octabam's platform takes pages off the bottom by moving the arena's base literal at its 23 sites and rewriting the four geometry words. Until 11 Oct 2026 it took a fixed 1,707 pages (10,487,808 B) in every remix with a DRAM unit.

The reserve now holds exactly what is claimed, in whole pages:

| claim | declared by | where |
|---|---|---|
| the linked runtime (code and data) | each `Linked(..., dram=True)` unit, plus the build's descriptor clones and label formatters | from the reserve's base |
| the runtime's `.bss` | the same units (KITS' library, PLOCKS P2's table) | after the runtime |
| the loader stage | the packed runtime, dead after the boot depack | page-aligned after the runtime |
| a `DramRegion` | the module (STEM REC's ring, stack and buffers) | stacked down from the reserve's ceiling, below any fixed claim |
| an `ArenaReserve` | the module, at a fixed address (REMIX SWITCH's image stage `0x41200000..0x41495de0`, Analog BD's pre-boot upload scratch `0x40b00000..0x40c00000`) | the reserve reaches past it |

The build links the runtime once at the largest reserve the arena allows (`arena.MAX_RESERVE`, which leaves `arena.MIN_PAGES_LEFT` pages) to find the runtime's top. It then takes the fewest pages that hold that top, every region and every fixed claim (`platform_build.pages_needed`), and links again at that size. If the packed stage grew past the reserve in that link, it adds a page and links once more. The report prints:

```
=== MEMORY: the platform's arena reserve ===
  <module>    <units>  <code+data>  <.bss>
  (descriptor clones) / (label formatters) / (link alignment) / loader stage
  <module> <region>       DramRegion at <address>
  <module> <claim>        ArenaReserve at <address>
  arena: octabam platform takes N pages at the bottom, <base>..<end> (<bytes>)
  arena: base <new base>, <pages> pages (<MB>) left for samples and recorders (stock 14,602)
```

## The gate

`tools/verify/verify_reserve_writes.py <remix>` (MEMORY's module gate on octabam-bus and bus, `gate.py`, once per shared round) runs `verify_set` (the gate project, loaded and playing) with every write into the pages the reserve gave back (its ceiling up to `0x41495de0`, the fixed reserve's end) recorded when the writing PC lies outside stock's code (`ot_emu --foreign-writes`). A write from a module there is a claim it never declared. What it cannot see:
- writes on paths the set does not exercise (a menu, a sample load, a recorder take, a switch);
- a module that calls a stock routine (memset, memcpy) or pokes stock code into writing there, since the PC is stock's;
- writes inside the reserve or above `0x41495de0`.

## Refusals

- The ledger: declared regions and fixed claims past `arena.MAX_RESERVE`; two fixed claims that overlap; a fixed claim in a remix with no DRAM unit.
- The build: a fixed claim under the runtime, its stage or its `.bss`; a reserve that would leave fewer than `arena.MIN_PAGES_LEFT` pages.
- A module that declares a `DramRegion` or an `ArenaReserve` requires MEMORY (STEM REC, REMIX SWITCH, ANALOG BD).

## Declaring a claim

```python
from remix.schema import ArenaReserve, DramRegion

dram_regions=(DramRegion("my_ring", 0x100000),),               # linked by symbol
arena_reserves=(ArenaReserve("my stage", 0x40b00000, 0x40000),),  # fixed address
requires=("MEMORY",),
```

A unit's `.bss` needs no declaration; the link measures it.

## Stock's page pool, measured (11 Oct 2026)

Read from the 1.40C disassembly, then run under the port (`tools/harness/pool_probe.py`). The project was the tone project of `tools/harness/usb_sig_project.py`: eight Flex samples of 2 s stereo 16-bit, one per track, `RESERVED_RECORDER_COUNT=8`, `RESERVED_RECORDER_LENGTH=16`, 120 BPM. The images were `bus` (2-page reserve) and `bottleservice` (535 pages). ✅ marks a reading confirmed by a port run; the others are from the disassembly.

### Globals and tables

| address | what |
|---|---|
| `0x80006914` | pointer to the page list, `0x46c2e9c0`: 16-bit page numbers. Entries `0 .. used` are the Flex slots' pages, `used .. total` are free |
| `0x80006918` | pointer to the slot start table, `0x46c2e580`: 136 longs, each slot's first index in the list |
| `0x8000691c` | pages in use by Flex slots ✅ |
| `0x80006920` | pages the list holds: the arena count less what the recorders took ✅ |
| `0x46c75e88` | 136 words: each slot's page count ✅ |
| `0x46c922c4` | 136 records of 44 B: the slot state the release resets |
| `0x46c2e9c0 + (r + 2) x 14,602 x 2` | recorder `r`'s own page list (slots 128..135 = recorders 0..7) ✅ |

A page's address is `arena base + page number x 6,144`; page 0 is the header slot. There are no owner rows: a page belongs to the slot whose list range holds its number.

### The routines

- **Cold init** `0x40096f24`. Called from 6 sites: main init `0x4001fbb4`, and `0x40085176`, `0x400853b2`, `0x40085494`, `0x400854c8`, `0x40085ba0`. It writes the list 1..count in order, sets used to 0, resets all 136 slots and clears the whole arena with one `memset` (`0x40097006`).
  - ✅ It ran twice in a boot that loads a project: at main init, and again inside LOAD PROJECT.
- **Flex slot allocate** (in `0x40096548`, called from `0x40084b4a`; the allocation is at `0x40096914`). Runs with interrupts masked. A bump allocator: slot start = used, used += request, slot count = request.
  - Returns −46 if the slot already holds pages and −5 if the request exceeds total − used.
  - ✅ 8 slots × 58 pages. Each slot's pages were one ascending run. Slot 7 was loaded first and holds pages 1..58.
- **Recorder pages** `0x40095a90`, called from `0x40085bfc`, `0x40096368`, `0x400968ee`. A recorder takes pages off the top of the list into its own list, and the total drops by the same amount.
  - ✅ 8 recorders × 690 pages. Each is one run in descending page order (14,600 down to 13,911 on `bus`).
  - ✅ The total fell from 14,600 to 9,080 on `bus`, and from 14,067 to 8,547 on bottleservice.
- **Slot release** `0x40096300`, called from `0x40025308`, `0x4008598e`, `0x400965b2`, `0x4009694e`. For a Flex slot it:
  1. zeroes each of the slot's pages (`0x40020984`, 6,144 B each);
  2. rebuilds the list in a shadow copy (`0x46c35bd4`, starts at `0x46c2e7a0`) that leaves the freed page numbers right after the in-use region and moves every later slot's start down;
  3. swaps the two pointers with interrupts masked, copies the result back and swaps again;
  4. lowers used by the slot's count.

  A recorder slot goes back through `0x40095a90`.
  - ✅ `call 0x40096300 3`: used fell from 464 to 406. The starts of slots 4..7 fell by 58. Every slot's own page numbers were unchanged.

### Contiguity

✅ After a load, every Flex slot and every recorder holds one physically contiguous run.

A release hands its page numbers to the next allocation first, so a later request larger than the freed run spans more than one run. Contiguity after a release followed by a larger load is inferred from the code, not run.

### Free pages on a project

✅ With the tone project: `bus` had 14,600 pages, 9,080 after the recorders, and 8,616 free with the eight samples loaded. bottleservice had 14,067, 8,547 and 8,083.

The fixed 1,707-page reserve would have left bottleservice 12,895, 7,375 and 6,911 (arithmetic, not run).

A project that fills Flex RAM was not measured; the tone project's samples total 464 pages.

### Why the reserve is sized at build, not taken at run time

These facts are the record of why MEMORY does not take pages through stock's allocator while the unit runs:
- ✅ LOAD PROJECT runs the cold init again. It rewrites the list, resets all 136 slots and clears the whole arena. Pages a module took from the allocator would be zeroed and handed back to the next sample at every project load.
- The allocator takes a slot number (0..127 for Flex, 128..135 for the recorders). A module would need a slot the project's samples never use.

The reserve is therefore fixed when the image is built and sized from the claims. Stock never sees it: the arena's base literal moves past it.
