#!/usr/bin/env python3
"""Edit a Multica issue description without erasing a concurrent write.

`issue update --description-*` replaces the whole field, and the CLI exposes no
compare-and-set (no `--if-revision` as of v0.5.2; `revision` comes back on read
and cannot be passed on write). Two writers that read, edit and write back erase
each other in silence. This helper keeps the race window to the seconds between
its own read and its own re-read, and detects a write that lands inside it:

  1. reads the description, `revision` and `updated_at` immediately before
     writing — never reuse an old read;
  2. applies exact-substring replacements, each of which must occur exactly once,
     and/or appends a block; if the result is the text already stored, it stops
     without writing (an identical write moves no `revision`, measured on
     24/09/2026, and would read as a concurrent write);
  3. writes with --no-start, so no agent run starts;
  4. compares the re-read with what it wrote, ignoring trailing whitespace (a
     trailing newline alone produced false alarms on 21/09/2026) — this catches
     a write landing AFTER ours;
  5. requires `revision` to have moved by exactly one — our write. This is the
     check that catches a write landing BEFORE ours: ours erased it, so the
     re-read shows our text and the content comparison passes.

Usage:
  patch-description.py --workspace-id WS --issue LAS-123 --edits edits.json
  patch-description.py --workspace-id WS --issue LAS-123 --append block.md
  (both flags together: replacements first, then the append)

edits.json is a JSON list of pairs of two strings, [["old", "new"], ...], each
`old` non-empty; anything else exits 2 before the board is read, and so does an
empty append block.
Env: MULTICA_PROFILE (required), MULTICA_BIN (default: the desktop-app binary).

Exit codes:
  0  written, and the re-read matches
  1  nothing written: an `old` did not occur exactly once, the append is already
     there, or the edits leave the description unchanged
  2  CLI, file or usage error. It can also come AFTER a successful write, when
     the re-read fails; re-running is safe, because a replaced substring no
     longer matches and a repeated append exits 1
  3  written, but the window was not clean: the re-read differs (a write landed
     after ours), or `revision` did not move by exactly one. A jump is not proof
     of loss — comments, replies, title and status changes and writes the
     timeline does not show also move the counter. What decides is the timeline:
     more than one `description_updated` after the printed `updated_at` (ours is
     one of them) means a description write landed in the window; reconcile by
     hand before writing again
"""
import argparse
import json
import os
import subprocess
import sys

DEFAULT_BIN = ("/Applications/Multica.app/Contents/Resources/app.asar.unpacked/"
               "resources/bin/multica")


def load_edits(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not all(
            isinstance(p, list) and len(p) == 2
            and all(isinstance(x, str) for x in p) and p[0] for p in data):
        raise ValueError("--edits must be a JSON list of pairs of two strings, "
                         'the first non-empty: [["old", "new"], ...]')
    return [(old, repl) for old, repl in data]


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

    def cli(args, stdin=None):
        try:
            r = subprocess.run(base + args, input=stdin, capture_output=True, text=True)
        except OSError as e:
            raise RuntimeError(f"cannot run the CLI: {e}")
        if r.returncode:
            raise RuntimeError(r.stderr.strip())
        return r.stdout

    def read():
        d = json.loads(cli(["issue", "get", a.issue, "--output", "json"]), strict=False)
        return d["description"] or "", d.get("revision"), d.get("updated_at")

    try:
        edits = []
        if a.edits:
            edits = load_edits(a.edits)
        block = None
        if a.append:
            with open(a.append, encoding="utf-8") as f:
                block = f.read().strip()
            if not block:
                raise ValueError("the --append block is empty")
    except (OSError, ValueError, TypeError) as e:
        print(f"cannot load --edits/--append: {e}", file=sys.stderr)
        return 2

    try:
        fresh, fresh_rev, fresh_at = read()
    except (RuntimeError, ValueError, KeyError) as e:
        print(f"read failed: {e}", file=sys.stderr)
        return 2

    new = fresh
    for old, repl in edits:
        n = new.count(old)
        if n != 1:
            print(f"nothing written: substring occurs {n} times: {old[:80]!r}",
                  file=sys.stderr)
            return 1
        new = new.replace(old, repl)
    if block is not None:
        if block in new:
            print("nothing written: the append block is already there", file=sys.stderr)
            return 1
        new = (new.rstrip() + "\n\n" if new.strip() else "") + block + "\n"
    if new.rstrip() == fresh.rstrip():
        print("nothing written: the edits leave the description unchanged",
              file=sys.stderr)
        return 1

    try:
        cli(["issue", "update", a.issue, "--description-stdin", "--no-start"], stdin=new)
    except RuntimeError as e:
        print(f"write failed: {e}", file=sys.stderr)
        return 2

    try:
        after, after_rev, _ = read()
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
            print(f"WINDOW NOT CLEAN: revision went from {fresh_rev} to {after_rev}, "
                  "not exactly +1, and the re-read shows our text. Either a description "
                  "write before ours was erased by ours, or nothing was lost and the jump "
                  "came from a comment or another field. Decide by `issue timeline`: more "
                  f"than one `description_updated` after {fresh_at} (ours is one) means "
                  "a description write landed in the window", file=sys.stderr)
            return 3
    else:
        print("warning: no integer `revision` in the read; a write landing before "
              "ours cannot be detected", file=sys.stderr)
    print(f"{a.issue}: written and verified ({len(after)} characters, "
          f"revision {fresh_rev} -> {after_rev})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
