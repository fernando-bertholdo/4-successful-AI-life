#!/usr/bin/env python3
"""Re-apply LOCAL-PATCH blocks after an upstream sync overwrites a vendored dir.

The sync workflow does `rsync --delete` of the raw upstream over
`plugins/<name>/upstream/`, which wipes any local patches we added. Our patches
are delimited by sentinels:

    <!-- LOCAL-PATCH:start id=some-id -->
    ...our content...
    <!-- LOCAL-PATCH:end id=some-id -->

This script reads the committed (HEAD) version of each file under the given
directory, extracts those blocks, and re-injects any that the freshly-synced
file is missing — placing each block right after the same anchor line (the
nearest non-blank line that preceded it in HEAD). It only ADDS our own blocks;
it never edits upstream content. Worst case (anchor not found) it inserts the
block near the top and emits a warning, degrading to the old manual behavior
rather than corrupting the file.

Idempotent: a block already present in the synced file is left untouched.

Usage: reapply-local-patches.py <dir> [<dir> ...]
Exit 0 always (best-effort); prints what it re-applied.
"""

import re
import subprocess
import sys
from pathlib import Path

START = re.compile(r"<!--\s*LOCAL-PATCH:start\s+id=(\S+?)\s*-->")
END = re.compile(r"<!--\s*LOCAL-PATCH:end\s+id=(\S+?)\s*-->")


def git_head_version(relpath: str):
    """Return the committed (HEAD) text of a repo-relative path, or None."""
    r = subprocess.run(
        ["git", "show", f"HEAD:{relpath}"],
        capture_output=True,
        text=True,
    )
    return r.stdout if r.returncode == 0 else None


def extract_blocks(text: str):
    """Yield (block_id, anchor_line_or_None, block_lines) for each patch block."""
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = START.search(lines[i])
        if not m:
            i += 1
            continue
        pid = m.group(1)
        j = i
        while j < len(lines):
            e = END.search(lines[j])
            if e and e.group(1) == pid:
                break
            j += 1
        block_lines = lines[i : j + 1]
        # Anchor = nearest non-blank line before the start sentinel.
        k = i - 1
        while k >= 0 and lines[k].strip() == "":
            k -= 1
        anchor = lines[k] if k >= 0 else None
        yield pid, anchor, block_lines
        i = j + 1


def present_ids(text: str):
    return {m.group(1) for m in START.finditer(text)}


def frontmatter_end(lines):
    """Index just after a leading YAML frontmatter block, or 0 if none."""
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                return idx + 1
    return 0


def reapply(relpath: str, head_text: str, disk_path: Path) -> bool:
    blocks = list(extract_blocks(head_text))
    if not blocks:
        return False
    new_text = disk_path.read_text()
    have = present_ids(new_text)
    changed = False
    for pid, anchor, block_lines in blocks:
        if pid in have:
            continue  # upstream already carries it — don't duplicate
        lines = new_text.split("\n")
        if anchor is not None and anchor in lines:
            at = lines.index(anchor) + 1
            while at < len(lines) and lines[at].strip() == "":
                at += 1
            sep = [] if (at > 0 and lines[at - 1].strip() == "") else [""]
            lines[at:at] = sep + block_lines + [""]
            print(f"  re-applied LOCAL-PATCH id={pid} after anchor in {relpath}")
        else:
            at = frontmatter_end(lines)
            lines[at:at] = ["", *block_lines, ""]
            print(
                f"::warning::anchor for LOCAL-PATCH id={pid} not found in {relpath}; "
                f"inserted near top — verify placement"
            )
        new_text = "\n".join(lines)
        changed = True
    if changed:
        disk_path.write_text(new_text)
    return changed


def main(argv):
    any_applied = False
    for d in argv:
        base = Path(d)
        if not base.is_dir():
            print(f"::warning::not a directory: {d}")
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            relpath = path.as_posix()
            head_text = git_head_version(relpath)
            if head_text is None:
                continue  # new file, not in HEAD
            if reapply(relpath, head_text, path):
                any_applied = True
    if not any_applied:
        print("  no LOCAL-PATCH blocks to re-apply")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
