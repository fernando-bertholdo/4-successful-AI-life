---
name: smart-rename
description: Manage the smart-session-rename plugin. Phase 1 prototype supports freeze/unfreeze only.
---

# /smart-rename (Phase 1 prototype)

When the user invokes `/smart-rename freeze` or `/smart-rename unfreeze`, run the matching command via the Bash tool and report the output verbatim.

## How session id is determined

Empirical finding (Phase 1.3 smoke test): `$CLAUDE_SESSION_ID` and `$CLAUDE_TRANSCRIPT_PATH` are NOT exposed as env vars when a skill invokes Bash. The CLI therefore derives the session id from `pwd -P`: it scans `~/.claude/projects/<encoded-cwd>/` for the most recently modified `.jsonl` and treats that as the active session.

If the derivation fails, the CLI exits 1 with `ERROR: cannot determine session id` and prints what it tried.

## Commands

### `/smart-rename freeze`

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh freeze
```

### `/smart-rename unfreeze`

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh unfreeze
```

## Debug

If something goes wrong, re-run with debug tracing:

```bash
SMART_RENAME_DEBUG=1 ${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh freeze
```

Any other subcommand: reply "Not yet implemented (Phase 1 prototype)."
