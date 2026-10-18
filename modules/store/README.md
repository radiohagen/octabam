# STORE

Platform module. Holds the stock sites where a project's side files are
written, read, copied and cleared, and where a Part is saved or cleared. The
ledger allows one detour on a site; KITS and PLOCKS P2 each hooked some of
these sites, so the sites are held once here and each module is a client that
STORE calls at the event.

## Events

| event | stock site | arguments to a handler |
|---|---|---|
| loadall_pre / post | `0x40090504` (load of every bank) | none |
| loadmask_pre / post | `0x400905d4` (masked bank load) | d1 = mask, d2 = return address |
| newproj | `0x400909d8` (new, empty project) | none |
| newproj_post | after the same native routine returns | none |
| bankw_guard | same bank-writer site, before bankw_pre | d1 = bank mask; checked result |
| bankw_pre | `0x400918aa` (inside the bank writer, after the project directory exists) | d1 = mask of banks written |
| bankw_post | `0x400917c8` (bank writer, after it returns) | none |
| pstore_pre / post | `0x4008ee74` (project store) | none |
| preload_post | `0x4008f180` (project reload) | none |
| bankcopy_guard | before stock file copy or any bankcopy clients | d0 = destination, d1 = source; checked result |
| bankcopy_done | after successful stock copy and existing bankcopy clients | d0 = destination, d1 = source, d2 = native result; checked result |
| bankcopy | `0x4008ee42`, `0x4008f14e`, and the four `d5` loads at `0x4008ef9a`, `0x4008f02e`, `0x4008f2a6`, `0x4008f33a` (stock `.work` / `.strd` file copy) | d0 = destination path, d1 = source path; after stock's successful copy |
| tocs1 | `0x4000faf0` (current bank into CS1) | d0 = bank; before stock's copy |
| fromcs1 | `0x40025808` (power-up bank from CS1) | d0 = bank; after stock's call |
| partsaved | `0x4004a9c4` (Part Save tail) | d0 = part |
| partclear | `0x4004a9d0` (Part Clear entry) | d0 = part |
| ctl (not an event) | `0x40061e00` (the encoder dispatch call) | opens the refusal prompt, scrolls it; else KITS' list scroll or stock's dispatch |

A handler may clobber every register. Handlers of one event run in the order
of `CLIENTS` in `manifest.py`. Wrappers keep one return slot per event and do
not re-enter.

The optional `bankw_guard`, `bankcopy_guard` and `bankcopy_done` phases
return d0: nonnegative continues, negative stops that phase and returns the
error through stock's normal path. `bankw_guard` runs before `bankw_pre` and
native bank writes; `bankcopy_guard` runs before any native or companion copy.
Both `bankcopy` and `bankcopy_done` only run after a successful native copy.
A failure from `bankcopy_done` is returned but cannot undo copies already
made. These phases are ordered, not transactional. The original notification callbacks keep their existing
void-result contract. Optional code and tables are omitted when unused.

Arguments are preserved separately from each callback's registers. A client
may clobber d0-d7/a0-a6, but must balance its stack. STORE owns native calls,
continuations and error exits; clients return normally.

## Clients

`CLIENTS` in `manifest.py` lists, per module key, the symbol prefix and the
events it handles; the handler for event `e` is `<prefix>_st_<e>`. A client not
in the remix is left out of the tables, and a handler named there that the
link cannot find stops the build. A client declares `requires=("STORE",)`.

| client | events |
|---|---|
| PLOCKS P2 (`plk`) | loadall_pre, loadmask_pre, newproj, bankw_pre, bankcopy, tocs1, fromcs1 |
| KITS (`kits`) | loadall_pre/post, loadmask_pre/post, newproj, bankw_post, pstore_pre/post, preload_post, partsaved, partclear |
| MIDI SCENES (`scn`) | loadall_pre/post, loadmask_pre/post, newproj, bankw_post, pstore_pre/post, preload_post, tocs1, fromcs1, partclear |
| MIDI HARMONY (`ch`) | loadall_post, loadmask_post, newproj, newproj_post, bankw_guard, bankcopy_guard, bankcopy_done, tocs1, fromcs1 |

Harmony reads companions after native banks and KITS are available. Its
checked save prevents native/P2 writes after a failed Harmony write; its copy
guard preserves stored bank backups after that failure. P2 precedes Harmony
on restore. Each client owns its retained allocation and file context.
`CLIENT_IDS` is the separate, optional refused-file UI registry; a lifecycle
client need not implement that UI. Harmony retains its existing companion
validation and native save-error behavior.

## Caller census

Every caller of `0x40090504` (1), `0x400905d4` (3), `0x400909d8` (5, one
pc-relative), `0x400917c8` (5, one pc-relative), `0x4008ee74` (3) and
`0x4008f180` (1) in the stock image is a direct call; a byte search of the image
for each address finds only those call operands (10 Oct 2026). PLOCKS P2's
call-site hooks covered every caller of the load and new-project routines, so
an entry hook sees the same calls.

## File calls

`store_path`, `store_fopen`, `store_fread`, `store_fwrite`, `store_fclose`
and `store_crc32` (running value in d1, 0 to start). A client owns a 4,120-byte
context (stock file object and its 4 KB buffer), so one client's open file is
never another's. `scenes.work` uses them; KITS and PLOCKS P2 keep their own
copies.

## Refused files

A client that cannot use a file (unknown version, bad length or CRC) calls
`store_refuse(client id, argument)` and leaves the file alone: it is never
written over. STORE lists up to 16 refusals (`store_pend`, `store_npend`,
cleared at a load of every bank). At the first encoder turn after the load
(the only UI-task site STORE holds; a list cannot be opened from the engine
task) a dialog names the file and explains which saved data could not be
loaded: FX page 2 locks, saved Kits or MIDI scenes. It says UNREADABLE OR
INCOMPATIBLE and offers NO: KEEP FILE / YES: OPTIONS.
YES opens the three recovery choices. NO keeps the
file protected and dismisses the prompt until the next project load:

| row | answer | what the client does |
|---|---|---|
| KEEP FILE / SKIP SAVED DATA | `ANS_IGNORE` | keeps the file protected and does not load its saved data |
| START FRESH / REPLACE FILE | `ANS_OVERWRITE` | starts empty (KITS: as a missing file, the stock Parts become Kits); the next save replaces the original file |
| BACKUP FILE THEN START FRESH | `ANS_BACKUP` | starts fresh, and the next save first copies the original file to `.bak` |

This is recovery, not a format upgrade: the old saved data is not converted.
The prompt can also appear for damaged or incomplete files, not just files
from development builds. The exact cause needs the refused file to be examined.

LEVEL scrolls the list; YES answers; NO closes it without an answer, leaving the
entries listed and asking no more until the next load. No answer touches the
card: the callbacks run in the UI task and the save in the engine task (a file
copy called through the port's `--call` never returned). Client ids: 0 PLOCKS P2
(argument = the bank), 1 KITS, 2 MIDI SCENES. PLOCKS P2 used to read a refused
`p2lkNN.work` as empty and overwrite it at the next bank write.

## Measured

Under the port (10 Oct 2026): `verify_kits` (the refused `kits.work`: listed; OVERWRITE
and BACKUP read it as a missing file; the list opens at an encoder turn, LEVEL + YES
answers OVERWRITE, YES on row 0 answers IGNORE), `verify_plocksp2` (a bad `p2lk` header is
listed and survives SAVE PROJECT), `verify_scenes --persist` (a bad `scenes.work` stays byte
for byte under IGNORE; OVERWRITE and BACKUP give a good file, BACKUP also `scenes.bak`).
15 Oct 2026 (#742): `verify_kits` also checks the initial information
dialog, YES opening the choices, and NO keeping the file protected without
reopening on another encoder turn. `verify_plocksp2` exercises the same
information, choices and cancellation with a refused lock file, capturing
the LCD for review. Not covered: a list opened over another window, the
new prompt on a unit.

[Contribution verification](DEVELOPMENT.md).
