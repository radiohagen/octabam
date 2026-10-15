# radiohagen MIDI contribution workspace

This fork keeps `main` equal to sambanks/octabam. The complete MIDI-only
integration is `codex/integrate/midi`. It is an acceptance workspace, not a
single upstream pull request. See [the staged PR plan](MIDI_UPSTREAM_PLAN.md).
Author source is [radiohagen/octatrack-modules](https://github.com/radiohagen/octatrack-modules).

Local convention: `origin` fetches sambanks/octabam; `fork` pushes to
radiohagen/octabam. Authentication and author identity are local to dedicated
radiohagen checkouts. `git gh` invokes the isolated radiohagen CLI profile.
Plain `gh` and the app's GitHub connector retain mattiaswolff; do not use them
for writes to this fork. Do not change global credentials or existing checkouts.

Use separate worktrees. The author repo's guarded staging command handles
native-path source synchronization. Per-module external adapters remain a
separately verified contribution step; do not claim them completed.

Preserved local firmware, fixtures and raw test logs remain in the original
finished worktree's ignored output directories. Only source, documentation and
sanitized validation records are published. No hardware acceptance is implied.
