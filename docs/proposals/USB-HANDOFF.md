# USB merge takeover — 15 October 2026

**Read this before doing more diagnosis. The load hang has been isolated;
several attractive earlier explanations were falsified.** Sam asked to stop
for credits and commit a complete handoff. No PR was opened or merged.

## Worktrees and scope

Repository: `/Users/sambanks/git/octabam`. Never edit the main checkout.

1. `.claude/worktrees/usb-module`, branch `usb-module`:
   - Rebased onto `origin/main` = `2d1cbcf4`.
   - `b3dc3d7b`: merges the four USB modules into `modules/usb/`.
   - `b2a35a51`: fixes symbol lookup to use each linked unit's own symbols.
   - This handoff commit also fixes three manual site pages and preserves
     the inherited notes in `USB-PROGRESS.md`.
2. `.claude/worktrees/ata-write-guard`, branch `codex/ata-write-guard`:
   - Started from the same `origin/main`, independently of the USB merge.
   - WIP implementation commit: `e867e1c6` (cherry-pick only after validation).
   - Contains the new ATA WRITE GUARD module, isolated test remix,
     instruction-level probe and gate. Committed as work in progress;
     its newly integrated gate and full `make check` are NOT yet certified.
   - It is NOT yet selected by any shipping remix or integrated into USB.

The user's eventual objective is one USB module with on-device channel and
feature selection. The inherited handoff explicitly limited its previous
agent to proving phase 1. Current USB code is phase 1 ONLY: LAYOUT/INPUTS
are `Apply.BUILD`. On-device settings are still unimplemented. Do not claim
that completing the merge implements the final user objective. The USB
branch's `docs/proposals/USB.md` sections 5, 8 and 9 contain phases 2–4:
all-six output producers and dispatch, parametric input inject, descriptor
sets and selector, NEXT_BOOT settings, early persistence and invalid-pair
edit behavior. The early CS1 settings store is not implemented yet.

Original external notes: `~/Downloads/USB-PROGRESS.md`. Original PR draft:
`/tmp/usb_pr_body.md` (stale; do not publish without rewriting results).

## Confirmed diagnosis of the load hang

The BUILD=0 vs BUILD=1 difference is NOT a server-name parser defect.
Only server-name runtime bytes change, but boot packing/timing changes
which interrupt window is hit. The name read watch logged no name reads.

Stock first-sector PIO write:

- `0x40014cdc`: saves SR in d0, then raises SR to `0x2700`.
- `0x40014ce4`: issues WRITE; stores command state 2.
- `0x40014cf2`: restores SR too early.
- `0x40014d0c..36`: sends the first 256 words.
- `0x40014d38..52`: advances buffer pointer at `0x46c8c594` and
  decrements remaining-sector byte at `0x46c8c592`.

Observed failure: the engine is preempted at `0x40014d34` after the final
word but before those updates. Completion IRQ then runs in sys, sees count
1 and the old pointer, and polls DRQ in `0x4001551e/24/26` forever. The
card already finished the one-sector command: status `0x50`, DRQ clear.
The lower-priority engine cannot resume to fix its count.

Direct diagnostic captured at emulated 13053.981 ms:

```
status=50 dpos=512 dsize=512 irq=0 due=0
writes=5705 flag=1 state=2 ptr=4eceb200 cmd=30
last command WRITE lba=2301 count=1 pc=40014ce4 tcb=460ddde4
```

Engine TCB `0x460ddde4`, saved SP `0x460dd8ac`; exception PC
`0x40014d34`. Stack includes stock buffered close, stock logger, and
static sample-load error logger return `0x400908ca`. The copied fixture
has absent sample files and exercises stock logging. The handoff's focus
on `brain_on_job` was misleading: that hook handles all engine jobs.

This interruption window and its repair are measured under the port.
Whether it occurs with real card timing is NOT measured. Do not present
this as a confirmed hardware failure or ship a new guard as hardware-proven.

### The experimentally successful repair

At `0x40014cf2`, replace `move.w d0,sr` with `move.w d0,d3`: retain saved
SR and keep the existing mask of 7 raised. d3's state value was already
stored; the loop does not use d3. Detour `0x40014d58` to a ten-byte DRAM
return stub that restores SR, returns d2 in d0, pops saved d2/d3 and RTS.
This includes all first-sector words AND pointer/count bookkeeping in the
existing critical section. No waits or filesystem calls are added inside.
The duration/delay added on hardware still needs measurement.

Using the exact failing old BUILD=0 image, with only these patches and a
stub preloaded into reserved DRAM at `0x4105e000`, the full DSP-enabled
load PASSED at instruction 2256855699, 20243.8 ms after the post.
Log: `/tmp/codex-usb-diag/b0-first-sector-guard-dram.log`.

A separate fast instruction-level prototype requests level-5 IRQ at the
last data word. It reproduces stock's stale bookkeeping and proves the
patched ordering, without relying on a build tag or long boot:

```
stock: 256 words, 1 IRQ, remaining_at_ack=1, ptr_at_ack=46020000
 guard: 256 words, 1 IRQ, remaining_at_ack=0, ptr_at_ack=46020200
both: d0=1, d2=11223344, d3=55667788, SP=4601000c, SR=2000
```

Prototype: `/tmp/codex-usb-port-debug/ata_race.cpp`; executable
`/tmp/codex-usb-port-debug/build/ata_race`. These results are real passes;
the expanded repository gate with five caller IPL values is still pending.

## New guard implementation: files and remaining validation

In `ata-write-guard` worktree:

- `modules/ata-write-guard/{manifest.py,guard.s,README.md}`: independent
  CF_PATCH, Category.FIXES, author sambanks, Proof.PORT. One asserted poke,
  one asserted detour, ten-byte stateless DRAM return unit.
- `remixes/test/ata-write-guard/{remix.py,README.md}`: stock 14 effects
  plus the guard, not a shipping remix.
- `tools/harness/ata_write_probe.cpp`: actual stock routine in the ColdFire
  Machine; negative stock control; guarded IPL 0,1,3,5,7; checks all 256
  word values, interrupt ordering, pointer/count, return status, saved
  d2/d3, SP and restored interrupt mask.
- `tools/harness/ata_write_probe/CMakeLists.txt`: builds only this probe
  against the repository's ot_machine in its OWN build directory.
- `tools/verify/verify_ata_write.py`: builds the isolated probe and the
  named remix, then loads its actual runtime into Machine and runs tests.
- `make docs` generated index changes in README.md and remixes/test/README.md.

The common emulator/CMakeLists.txt was deliberately left unchanged. The
new probe does not change emulator semantics or invalidate the shared port
source key. It builds under `out/ata_write_probe`; never modify vendor or
symlink out/emu. `vendor`/.venv are shared symlinks, stock slice was copied,
submodules initialized, and `make emu-get` was started in this worktree.

Next steps, in order:

1. Read `/tmp/codex-ata-probe.log`: the integrated gate was running at
   handoff. If still running, let it finish rather than start duplicates.
   Command: `python3 tools/verify/verify_ata_write.py ata-write-guard`.
   Its configure/build output is captured until failure/completion, so an
   empty log is not evidence of a hang. Check `/tmp/codex-ata-emu-get.log` too.
2. Fix any real compile/gate issues. Small cleanup: the C++ usage text
   still says `ot_ata_write_test`; actual executable is `ata_write_probe`.
   Consider pinning the freshly assembled guard unit with Linked.reference
   if appropriate; there is no outside author's port being rewritten here.
3. Run `python3 tools/verify/verify_docs.py`, `git diff --check`, then
   `make check REMIX=ata-write-guard` (the floor). Do not equate the
   diagnostic binary pass with a fully validated integrated module.
4. Add the new trap entry to docs/contributing/TRAPS.md and its AGENTS.md
   line, plus concise storage/placement/testing documentation as warranted.
   That documentation work is NOT done yet. Keep measurements/inference
   distinct. No flash or CHANGELOG entry: nothing was flashed.
5. Decide shipping composition cleanly: likely cherry-pick the independently
   reviewed guard commit(s) into usb-module and select ATA WRITE GUARD in
   the three official CORE tuples. No selection has been added yet.
   Do not hide this generic card fix inside USB assembly or change BUILD=0
   to 1 merely to dodge the race. Preserve the existing per-unit lookup fix.
6. Rebuild and rerun the actual loadmeter gate on the composed bus image,
   including its publish-off, OTOP-off and calibration variants. A successful
   single project load is not the complete loadmeter gate.
7. Update shipping remix READMEs/manual pages and generated indexes for any
   composition change. Rebase onto fresh origin/main, run required reach
   on that tree, record EACH command/result, then make a reviewable PR.
   No PR/merge authorization was newly requested during this takeover.
8. Only after phase 1 is proven, implement the user's runtime USB objective
   from the phase plan. No runtime USB implementation has been started.

## USB validation so far (rebased tree before any guard composition)

- `scripts/refhash.sh check`, via reach: ALL 24 CASES BIT-IDENTICAL against
  the fresh merge-base 2d1cbcf4 baseline. This validates the build change,
  not all USB/BRAIN behavior.
- `make identity`: finished. 34 fully identical; 28 report-only (firmware
  bytes identical); exactly three changed firmware images: octabam-bus,
  octabam-core, octabam-inserts. waveload and waveload-port fail on BOTH
  sides. The tool groups report-only cases into its printed “31 changed”.
  Log `/tmp/codex-usb-identity.log`; machine list out/identity/changed.json.
- `python3 tools/verify/verify_docs.py`: 55 modules, 67 remixes, 0 problems,
  after removing scratch remix. `git diff --check` passed for manual edits.
- octabam-bus per-remix checks passed (read its log; a pass with SKIP is
  not strict acceptance). octabam-core passed, one SKIP, 2105 s.
- cfmeter-post fails verify_usb vendor-counter assertion with 4 overruns.
  Distinct from the inherited notes' M6a failure. Its image is byte-identical
  to main, so this is NOT evidence of a USB-merge firmware regression;
  confirm gate parity before dismissing it. Do not weaken the assertion.
- The first reach snapshotted an untracked scratch remix before it was
  moved away. Its docs/selftest failures from bus-layout-off are artifacts
  of that scratch, not shipping behavior. Scratch preserved at
  `/tmp/codex-usb-bus-layout-off-scratch`. verify_docs passes without it.
- `make test-acceptance` printed 247 tests OK, one skipped. Final overall
  reach table is still pending; do not report reach green.

## Background jobs: do not overwrite their output while they run

At ~20:03 AEDT, these jobs were still alive:

- USB `make reach RUN=1 KEEP=1`: `/tmp/codex-usb-reach.log`;
  parent reach PID 78869, check_shards PID 79693. Shards under out/shards.
  Two old loadmeter processes are expected to reproduce the UNGUARDED
  hang: emulators 44939 and 47837, parents 43331 and 46283. Their watch
  logging makes them slow. Inspect ownership before terminating anything.
- USB `make check-shared REMIXES='octabam-bus octabam-core octabam-inserts'`:
  `/tmp/codex-usb-shared-clean.log`, make PID 48517. This reruns shared gates
  without the scratch remix and was in verify_kits at handoff. It writes
  root out/, so do not build another image there concurrently.
- New guard gate: `/tmp/codex-ata-probe.log`, separate worktree/out.

Read tails and process state before launching any repeat. Do not restart
check_shards over existing live shards. After changes/new commits, rerun
reach only once previous work has finished; cached results save time.

## Falsified leads and scratch artifacts

All binaries/images/dumps below are PRIVATE local artifacts, never commit
or upload them. They may contain Elektron bytes. Only source/docs in commits.

`/tmp/codex-usb-diag` contains a controlled fixture card and diagnostics:

- b0.bin reconstructed from `/tmp/rt_b1/runtime.raw` (despite its name,
  that file contains BusVerb0/BusDelay0). Exact expected packed length
  0x1241f and image length 1,187,683. b1 original `/tmp/img_b1_maincue.bin`.
- main-b0.bin copied from inherited usb-cfmeter-main/out; same emulator
  and card loaded successfully, instruction 2256575080 / 20243.8 ms.
  Log main-stage.log. Thus baseline evidence is fresh, not only cached.
- original-stage.log and relocated-stage.log both time out at 90000 ms.
  Relocating packed stage outside .bss does NOT fix the hang. Never change
  the loader merely because stage overlaps BRAIN scratch; that is intentional.
- b0-cf-only.log and b0-stage-outside-bss-cf-only.log both pass at EXACTLY
  instruction 2235061050. Without DSPs this diagnostic does not exercise
  the timing that exposes the bug.
- b0-exact-dsp.log (`--dsp-lazy 0`) fails with identical stuck dispatch
  counts: 13066 forces, 25267 dispatches. Lazy batching is not the cause.
- b0-stack.log, engine-{tcb,stack}.bin: 25000 ms bounded run with PC ring
  and task stack. Those are the direct stack evidence above.
- b0-card-state.log and b0-commands.txt: isolated instrumented emulator
  logs final card state/last commands, source copy in
  `/tmp/codex-usb-port-debug`. No repository port source edits were made.
- b0-ata16.log uses latency16 but only 25000 ms budget. It times out WHILE
  PROGRESSING, 19637 forces / 37530 dispatches, unlike the stuck signature.
  Do not say “latency16 reproduces the same hang”; its budget was too short.
- b0-first-sector-guard.bin / guard-panic.* are a FAILED first experiment:
  the stub appended at 0x40122364 faulted at that address with vector 0x0b
  on first write. Boot append space is not persistent runtime storage.
  The successful test uses b0-first-sector-guard-dram.bin and
  `--preload 0x4105e000=.../guard-epilogue.bin`, inside the arena reserve.

Successful full diagnostic command (run from USB worktree):

```
out/emu/ot_emu --image /tmp/codex-usb-diag/b0-first-sector-guard-dram.bin \
  --preload 0x4105e000=/tmp/codex-usb-diag/guard-epilogue.bin \
  --card /tmp/codex-usb-diag/card.img --set BRAINSET --project BRAINPRJ \
  --load-ms 25000 --mount --mkii --dsp --frame
```

No cleanup of other sessions' worktrees, stashes, index or processes.
The inherited usb-cfmeter-main and usb-bisect-b29 worktrees were left intact.

## Final checkpoint before stopping for credits

The integrated `python3 tools/verify/verify_ata_write.py ata-write-guard`
finished successfully (exit 0). `/tmp/codex-ata-probe.log` shows PASS for
stock control and all five guarded IPL cases (0,1,3,5,7). This supersedes
references above to that specific gate being pending. Full `make check`
and shipping composition/validation are STILL outstanding.

Committed checkpoints:

- USB handoff/manual changes: `9b77bd19` on `usb-module`.
- Independent guard module and integrated gate: `e867e1c6` on
  `codex/ata-write-guard`.

If cherry-picking the guard onto USB, expect generated-index and possibly
add/add handoff conflicts. Preserve the USB module merge, keep the USB
branch's handoff, and regenerate README indexes with `make docs`; do not
replace the merged USB module index with the old four-module index from
the guard branch. The guard is still not enabled in shipping remixes.

Background validation jobs were left running to preserve their work;
inspect their logs/ownership before starting another build in those trees.
