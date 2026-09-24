#!/usr/bin/env python3
"""Edit a Multica issue description without erasing a concurrent write.

`issue update --description-*` replaces the whole field, and the CLI exposes no
compare-and-set (no `--if-revision` as of v0.5.2; `revision` comes back on read
and cannot be passed on write). Two writers that read, edit and write back erase
each other in silence. This helper keeps the race window to the seconds between
its own read and its own re-read, and detects a write that lands inside it:

  1. reads the description and `revision` immediately before writing — never
     reuse an old read;
  2. applies exact-substring replacements, each of which must occur exactly once,
     and/or appends a block;
  3. writes with --no-start, so no agent run starts;
  4. re-reads and requires `revision` to have gone up by exactly one — our write.
     This is the check that catches a write landing BEFORE ours: ours erased it,
     so the re-read shows our text and a content comparison alone passes;
  5. compares the re-read with the fresh read plus the edits, ignoring trailing
     whitespace (a trailing newline alone produced false alarms on 21/09/2026) —
     this catches a write landing AFTER ours.

Usage:
  patch-description.py --workspace-id WS --issue LAS-123 --edits edits.json
  patch-description.py --workspace-id WS --issue LAS-123 --append block.md
  (both flags together: replacements first, then the append)

edits.json is a JSON list of [old, new] pairs.
Env: MULTICA_PROFILE (required), MULTICA_BIN (default: the desktop-app binary).

Exit codes:
  0  written, and the re-read matches
  1  nothing written: an `old` did not occur exactly once, or the append is
     already there
  2  CLI or usage error
  3  written, but another write landed in the window: `revision` moved by more
     than one, or the re-read differs. A write before ours was erased by ours;
     read `issue timeline` for a `description_updated` that is not ours and
     reconcile by hand before writing again. `revision` moves on writes to other
     fields too, so this can also be a status or priority change — conservative
     by design
"""
import argparse
import json
import os
import subprocess
import sys

DEFAULT_BIN = ("/Applications/Multica.app/Contents/Resources/app.asar.unpacked/"
               "resources/bin/multica")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workspace-id", required=True)
    ap.add_argument("--issue", required=True)
    ap.add_argument("--edits")
    ap.add_argument("--append")
    a = ap.parse_args()
    if not (a.edits or a.append):
        ap.error("give --edits, --append or both")
    profile = os.environ.get("MULTICA_PROFILE")
    if not profile:
        print("MULTICA_PROFILE is not set", file=sys.stderr)
        return 2
    base = [os.environ.get("MULTICA_BIN", DEFAULT_BIN), "--profile", profile,
            "--workspace-id", a.workspace_id]

    def read():
        r = subprocess.run(base + ["issue", "get", a.issue, "--output", "json"],
                           capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr.strip())
        d = json.loads(r.stdout, strict=False)
        return d["description"] or "", d.get("revision")

    try:
        fresh, fresh_rev = read()
    except (RuntimeError, ValueError, KeyError) as e:
        print(f"read failed: {e}", file=sys.stderr)
        return 2

    new = fresh
    if a.edits:
        for old, repl in json.load(open(a.edits, encoding="utf-8")):
            n = new.count(old)
            if n != 1:
                print(f"nothing written: substring occurs {n} times: {old[:80]!r}",
                      file=sys.stderr)
                return 1
            new = new.replace(old, repl)
    if a.append:
        block = open(a.append, encoding="utf-8").read().strip()
        if block in new:
            print("nothing written: the append block is already there", file=sys.stderr)
            return 1
        new = new.rstrip() + "\n\n" + block + "\n"

    r = subprocess.run(base + ["issue", "update", a.issue, "--description-stdin",
                               "--no-start"], input=new, capture_output=True, text=True)
    if r.returncode:
        print(f"write failed: {r.stderr.strip()}", file=sys.stderr)
        return 2

    try:
        after, after_rev = read()
    except (RuntimeError, ValueError, KeyError) as e:
        print(f"written, but the re-read failed: {e}", file=sys.stderr)
        return 2
    if after.rstrip() != new.rstrip():
        print(f"CONCURRENT WRITE: expected {len(new.rstrip())} characters, found "
              f"{len(after.rstrip())}; someone wrote after our write",
              file=sys.stderr)
        return 3
    if isinstance(fresh_rev, int) and isinstance(after_rev, int):
        if after_rev != fresh_rev + 1:
            print(f"CONCURRENT WRITE: revision went from {fresh_rev} to {after_rev}, "
                  "not +1, and the re-read shows our text: a write landed before "
                  "ours and ours erased it, or another field changed — check "
                  "`issue timeline` before writing again", file=sys.stderr)
            return 3
    else:
        print("warning: no integer `revision` in the read; a write landing before "
              "ours cannot be detected", file=sys.stderr)
    print(f"{a.issue}: written and verified ({len(after)} characters, "
          f"revision {fresh_rev} -> {after_rev})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
