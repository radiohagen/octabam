#!/usr/bin/env python3
"""Which CI jobs a diff can reach, so a job runs only when the diff
touches its inputs (.github/workflows/ci.yml gates every job on this;
`make ci` locally still runs everything).

    python3 tools/verify/ci_paths.py --base origin/main
    python3 tools/verify/ci_paths.py --base <sha> --github-output

A job is affected when any changed path is under one of its prefixes
(JOB_PREFIXES). The direction is over-run, never under-run: a family
missed here means a job skipped for a change that needed it, so
families err broad. A Makefile, scripts/ or .github/workflows/ change
runs everything; no usable diff (workflow_dispatch, a shallow clone)
runs everything; `docs and links` has no entry because it always runs.
"""
import argparse
import json
import subprocess
import sys

# Job -> path prefixes that feed it. `docs` is absent: it always runs
# (the registry loaders and the doclinks scan cover the files no other
# family matches, e.g. a root .md).
JOB_PREFIXES = {
    "coldfire": ["tools/emu", "tools/patches", "scripts", "Makefile"],
    "dsp": ["tools/harness", "tools/patches", "scripts", "Makefile"],
    "acceptance": ["tools", "modules", "remixes", "scripts", "Makefile"],
    "reach": ["modules", "remixes", "tools", "scripts", "Makefile"],
    "site": ["docs", "modules", "remixes", "tools", "scripts", "Makefile"],
}


def affected(paths):
    """git-style changed paths -> {job: bool}. None/[] -> everything."""
    out = {job: False for job in JOB_PREFIXES}
    if not paths or any(p.startswith(".github/workflows/") for p in paths):
        return {job: True for job in out}
    for p in paths:
        for job, prefixes in JOB_PREFIXES.items():
            if any(p == pre or p.startswith(pre + "/") for pre in prefixes):
                out[job] = True
    return out


def changed_paths(base):
    """git diff --name-only <base>...HEAD; None when there is no diff
    to take (workflow_dispatch has no base)."""
    if not base:
        return None
    r = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return None
    return [p for p in r.stdout.splitlines() if p]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="", help="the merge-base side (origin/main, a sha)")
    ap.add_argument("--github-output", action="store_true",
                    help="print name=true/false lines for $GITHUB_OUTPUT")
    args = ap.parse_args()
    a = affected(changed_paths(args.base))
    if args.github_output:
        for job, hit in a.items():
            print(f"{job}={'true' if hit else 'false'}")
    else:
        print(json.dumps(a, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
