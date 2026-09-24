#!/usr/bin/env python3
"""Edit a Multica issue description without erasing a concurrent write.

`issue update --description-*` replaces the whole field, and the CLI exposes no
compare-and-set (no `--if-revision` as of v0.5.3; `revision` comes back on read
and cannot be passed on write). Two writers that read, edit and write back erase
each other in silence. This helper keeps the race window to the seconds between
its own count and its own re-read, and detects a description write inside it:

  1. counts the issue's `description_updated` events (N) BEFORE reading the
     description: a write landing between a read and a later count would enter
     N while the text in hand is already stale;
  2. reads the description immediately before writing — never reuse an old read;
  3. applies exact-substring replacements, each of which must occur exactly once,
     and/or appends a block; if the result is the text already stored, it stops
     without writing (an identical write still logs a `description_updated`,
     measured on 24/09/2026, and would count as someone else's);
  4. writes with --no-start, so no agent run starts;
  5. counts again (M) and requires exactly one new event, and that one by our
     own profile: an event's `actor_id` is the `id` that `multica user profile
     get` returns for the profile that wrote it (v0.5.3, 24/09/2026: all 9
     `description_updated` on LAS-147), read once before the count. New means an
     id absent from N, so old entries a capped read drops (`issue timeline
     --help`) do not shift the count. Until an event by our profile shows it
     reads again, up to three times a second apart (latency not measured); if
     none shows, the window is not verified, whatever else showed. Two sessions
     on one profile look alike: with ours late, theirs passes for ours;
  6. compares the re-read with what it wrote, ignoring trailing whitespace (a
     trailing newline alone produced false alarms on 21/09/2026) — this catches
     a write landing after ours.

Neither `revision` nor `--since` decides. `revision` also moves on a comment, a
status change and writes the timeline does not show, so a jump is no proof of a
description write. `--since T` drops the whole second of T, and the fresh read's
`updated_at` is, as a rule, the second of the issue's last event — the very
second a concurrent write lands in (measured on v0.5.3: an event at 20:07:03Z is missing
from `--since 20:07:03Z` and present in `--since 20:07:02Z`). The count uses
neither timestamp nor counter.

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
  1  nothing written: an `old` did not occur exactly once, an insertion (a `new`
     that contains its `old`) is already there, the append is already there, or
     the edits leave the description unchanged
  2  CLI, file or usage error. It can also come AFTER a successful write, when
     the re-read fails. Re-running re-reads first and exits 1 without writing
     if any edit is already there: a replaced `old` no longer occurs, an
     insertion's `new` is present, the append block is present
  3  written, but the window was not clean: the re-read differs, or not exactly
     one new `description_updated`, or none by our profile. It prints what there
     is to act on: the read's `updated_at`, `revision` before and after, each new
     event with its time and author (`actor_type`, `actor_id`) and the command
     that lists them.
     An erased text cannot be recovered through the CLI — the event keeps no
     text (`details` is empty) and there is no history command — so do not
     write over it again: ask the event's author to re-apply their change.
     An event whose `actor_id` is our own profile's (marked) does not say which
     session wrote it: ask whoever runs the other sessions on that profile —
     the `timeline` cannot tell them apart.
     With two or more new events but `revision` up by only one between read and
     re-read, only one write changed the text, and it says nothing was lost —
     the one place `revision` enters, and it never makes the window clean
"""
import argparse
import json
import os
import subprocess
import sys
import time

DEFAULT_BIN = ("/Applications/Multica.app/Contents/Resources/app.asar.unpacked/"
               "resources/bin/multica")
SETTLE_READS = 3
LOST = ("The erased text cannot be recovered through the CLI: the event keeps no text "
        "(`details` is empty) and there is no history command. Do not write over it "
        "again; ask the author of the other event to re-apply their change (to an "
        "agent, that means a mention, which starts a run). If the other event is "
        "marked [this profile], it does not say which session wrote it: ask whoever "
        "runs the other sessions on this profile; the timeline cannot tell them apart.")


def window(issue, fresh_at, fresh_rev, after_rev, seen, me):
    lines = [f"  our read: updated_at {fresh_at}, revision {fresh_rev}; "
             f"re-read: revision {after_rev}",
             f"  description_updated events new since our count ({len(seen)}; one "
             "should be ours):"]
    lines += [f"    {e.get('id')}  {e.get('created_at')}  {e.get('actor_type')} "
              f"{e.get('actor_id')} ({e.get('actor_name')})"
              + ("  [this profile]" if e.get("actor_id") == me else "") for e in seen]
    lines.append(f"  list them: multica issue timeline {issue} --action "
                 "description_updated --output json (no --since: it drops the "
                 "whole second it is given)")
    return "\n".join(lines)


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

    def events():
        out = cli(["issue", "timeline", a.issue, "--action", "description_updated",
                   "--output", "json"])
        return {e["id"]: e for e in json.loads(out, strict=False)}

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
        me = json.loads(cli(["user", "profile", "get", "--output", "json"]),
                        strict=False)["id"]
        before = events()
        fresh, fresh_rev, fresh_at = read()
    except (RuntimeError, ValueError, KeyError, TypeError) as e:
        print(f"read failed: {e}", file=sys.stderr)
        return 2

    new = fresh
    for old, repl in edits:
        n = new.count(old)
        if n != 1:
            print(f"nothing written: substring occurs {n} times: {old[:80]!r}",
                  file=sys.stderr)
            return 1
        if old != repl and old in repl and repl in new:
            print(f"nothing written: the insertion is already there: {repl[:80]!r}",
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
        for attempt in range(SETTLE_READS):
            if attempt:
                time.sleep(1)
            seen = [e for k, e in events().items() if k not in before]
            ours = [e for e in seen if e.get("actor_id") == me]
            if ours:
                break
        after, after_rev, _ = read()
    except (RuntimeError, ValueError, KeyError, TypeError) as e:
        print(f"written, but the re-read failed: {e}", file=sys.stderr)
        return 2
    info = window(a.issue, fresh_at, fresh_rev, after_rev, seen, me)
    if after.rstrip() != new.rstrip():
        print("CONCURRENT WRITE: the re-read differs from what we wrote (expected "
              f"{len(new.rstrip())} characters, found {len(after.rstrip())}): a "
              "description write landed after ours, and ours may be the one it erased. "
              "Re-running re-reads first and exits 1 without writing if any of our "
              "edits is still there (an `old` gone, an insertion's `new` present, the "
              "append present); otherwise it writes them all again. If another event "
              f"below landed before ours, ours erased it. {LOST}\n{info}", file=sys.stderr)
        return 3
    if not ours:
        print("WINDOW NOT VERIFIED: the re-read shows our text, but no new "
              f"description_updated by our profile showed in {SETTLE_READS} timeline "
              "reads, so a write that landed before ours cannot be ruled out"
              + (f"; any event below may be one ours erased. {LOST}" if seen else "")
              + f"\n{info}", file=sys.stderr)
        return 3
    if len(seen) > 1:
        if isinstance(fresh_rev, int) and isinstance(after_rev, int) \
                and after_rev - fresh_rev == 1:
            print("WINDOW NOT CLEAN, NOTHING LOST: other description writes landed "
                  "after our count, but revision moved by one between our read and the "
                  "re-read, so only one write changed the text: the others were "
                  f"identical to it or landed before our read\n{info}", file=sys.stderr)
        else:
            print("WINDOW NOT CLEAN: another description write landed after our count; "
                  "if it landed after our read, ours erased it (the re-read shows our "
                  f"text). {LOST}\n{info}", file=sys.stderr)
        return 3
    print(f"{a.issue}: written and verified ({len(after)} characters, one "
          f"description_updated, revision {fresh_rev} -> {after_rev})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
