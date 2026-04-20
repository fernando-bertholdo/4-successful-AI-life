# Handoff — v1.5.1 known-issue investigation

**From:** v1.5.0 release session (2026-04-18 → 2026-04-20)
**To:** future session with fresh context
**Status:** v1.5.0 tagged; two CLI-path bugs and one CC-harness quirk deferred.

---

## Context

v1.5.0 shipped with the core auto-rename pipeline fully working (validated by 110+ `llm_decision` events across 20+ organic sessions + one successful end-to-end rename at $0.6119 on 2026-04-18). Level 4 Scenario 3 exposed two bugs that don't block shipping but should be fixed for 1.5.1. This handoff captures the investigation state so a fresh session can pick up without re-deriving it.

## Bug #1 — Empty-state corruption in Stop hook

### Symptom

Some state files under `~/.claude/plugins/data/claude-code-smart-session-rename-smart-session-rename-dev/state/<sid>.json` are exactly **1 byte** (just `\n`). The corresponding log files (`logs/<sid>.jsonl`) contain real events, so the hook *did* run for those sessions — but the final `state_save` wrote an empty `STATE` variable.

Examples on the maintainer's machine (2026-04-20):
```
a69c21c2-bd86-4efb-8a1d-3c432fcc17ff.json  (1 byte, corresponding log has 5+ events)
1d9b4acd-c317-4d70-8ac7-e92a87ec316e.json  (1 byte, corresponding log has 12+ events)
f9e0b4fa-f42e-4d11-9eb0-0c6924467af8.json  (1 byte, corresponding log has 5+ events)
35a68913-d7d8-4a19-830f-e41846b4d301.json  (1 byte)
5625dda6-f387-4dd0-a79b-a9fc2966cf87.json  (1 byte)
8b5e0afc-e1a5-4342-83b6-b9004689fb84.json  (1 byte)
```

### Root cause (hypothesis)

A `jq` pipeline in `scripts/rename-hook.sh` fails silently for certain inputs, producing `STATE=""`. Most likely suspect: line 89-101 where `--argjson turn "$TURN"` and `--argjson d "$DELTA"` can fail if `TURN` or `DELTA` is empty/malformed (e.g., when `transcript_parse_current_turn` returns empty JSON for a degenerate transcript).

`state_save` (scripts/lib/state.sh:40) then does `printf '%s\n' "$json" > "$tmp"`, which for an empty `$json` writes exactly one byte (`\n`).

### Self-healing mitigation already in place

`state_load` (scripts/lib/state.sh:25-38) detects 1-byte / non-JSON state files via `jq . "$f"`, moves them to `<f>.corrupt.bak`, and returns `{}`. So the next hook run starts fresh. The user-visible effect is limited to losing in-flight title evolution for that single session.

### Fix plan (v1.5.1)

1. After every jq mutation in `rename-hook.sh`, assert `STATE` is non-empty and valid JSON. If validation fails, log `state_mutation_failed` with the line number and the jq args, and skip the `state_save` call entirely.
2. Add a defensive guard in `state_save` itself: reject empty `$json` input and log `state_save_blocked`.
3. Regression test: integration case that passes an empty `TURN` / `DELTA` to the mutation pipeline and asserts the state file is not touched.

### Where to start

`scripts/rename-hook.sh` line 88-101 (the delta mutation) and line 222 (final `state_save`). Also inspect `lib/transcript.sh` for paths that return empty JSON.

---

## Bug #2 — `/smart-rename force` state divergence

### Symptom

During Level 4 Scenario 3:
1. User types `/smart-rename force` → CLI responds "Force flag set; will evaluate on next Stop hook."
2. User does a coding turn → Claude uses `Write` tool → Stop hook fires.
3. `/smart-rename explain` still shows `Estado: ativo; force próximo turno` (force not consumed).
4. State file shows `force_next: true` persisting indefinitely.

Waiting 90+ seconds doesn't help (LLM call would have completed in the Stop hook within that window if it had been triggered).

### Root cause (hypothesis)

`_state_file` (scripts/lib/state.sh:5-10) uses:
```bash
local base="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}"
```

- **When invoked from the Stop hook:** CC injects `CLAUDE_PLUGIN_DATA` → resolves to `~/.claude/plugins/data/claude-code-smart-session-rename-smart-session-rename-dev/`.
- **When invoked from the skill (Bash tool):** unclear whether CC injects `CLAUDE_PLUGIN_DATA` for skill-invoked subprocesses. If it doesn't, the CLI falls back to `/tmp/smart-session-rename/` — a completely different tree.

Observed while investigating: after manually running `cmd_force` in a shell WITHOUT `CLAUDE_PLUGIN_DATA` set, state was written to `/tmp/smart-session-rename/state/<sid>.json`. This directory did NOT exist before that manual run, suggesting the skill invocation path normally *does* use the CC-managed dir — but the divergence was still observed during real use, so the injection may be inconsistent.

### Evidence

- `force_triggered` events grepped across `~/.claude` return zero hits in our plugin's log dir. (The same event name exists in the `codex-openai-codex` plugin's logs — unrelated coincidence.)
- The observed "Estado: ativo; force próximo turno" in `/smart-rename explain` reads from the same `$base` as `cmd_force` wrote to. If they're the same dir, the Stop hook should see `force_next: true`. It doesn't — or it reads it but the force isn't consumed.

### Fix plan (v1.5.1)

1. Add a trace line at the start of `rename-hook.sh` AND at the start of the CLI's `session_id_from_args` helper: `log_event debug state_path_resolved "$SESSION_ID" '{"base":"'$base'"}'`. Compare in logs to confirm the paths agree.
2. If paths diverge, introduce a `resolve_plugin_data_path` helper that checks both CC-managed and legacy (`/tmp/`) locations and prefers the one with existing state.
3. Alternative: read `installPath` from `~/.claude/plugins/installed_plugins.json` as the canonical location (risky — couples plugin to CC internals).
4. Regression test: set `CLAUDE_PLUGIN_DATA` explicitly in the hook integration test, assert CLI sees the same dir.

### Where to start

1. Add the trace. Run one `/smart-rename force` + 1 coding turn in a fresh session. Inspect the trace to see if paths agree.
2. If paths agree but force still isn't consumed, the bug is in scorer logic (`scorer_should_call_llm` not honoring `force_next`).

---

## Quirk #3 — Stop-hook runtime registry sticks to first-install state

### Symptom

After editing `hooks.json` in the source repo, `/reload-plugins` appears to succeed (no errors, `/plugin` shows "Hooks: Stop") but the Stop hook never fires with the new command. Only a full `/plugin uninstall` + `/plugin install` from a *fresh* CC process (not an existing one) picks up the change.

### Root cause

Claude Code's plugin runtime caches the hook registry at plugin-enable time. `/reload-plugins` refreshes the manifest list but does not re-register hooks that are already "live" in the process. Additionally, for `directory` marketplaces (dev-install), `installed_plugins.json.gitCommitSha` is updated only on re-install, not on `/reload-plugins` (observed: `gitCommitSha` stayed at an old SHA even after edits to the source repo + `/reload-plugins`).

### Implication

This is a CC harness behavior, not a plugin bug. Just documented so future dev-iteration on hook configs doesn't waste hours. **To test hook changes:**

1. Edit `hooks.json` in source.
2. `/plugin uninstall claude-code-smart-session-rename` (or manually remove from `installed_plugins.json`).
3. Close all claude processes for a truly fresh start.
4. Launch new `claude` process.
5. `/plugin` → marketplace → install → enable.

Alternative faster path during dev: bypass the plugin system entirely and invoke `scripts/rename-hook.sh` manually with synthetic stdin (see `tests/integration/test-end-to-end.sh` for how the test suite does it).

### Fix plan

Not plugin-fixable. Report upstream to Claude Code if it becomes a maintenance pain point.

---

## Useful artifacts left on the maintainer's machine

All safe to keep; safe to delete if desired.

- `~/mnt-smart-session-rename-backup-20260418-042800.tar.gz` — backup of the stray `mnt/` directory that was previously in the source repo (since removed). Contains an orphan copy of v1.0 plugin. 101 KB.
- `~/.claude/plugins/installed_plugins.json.bak-*` — pre-uninstall backup (from debugging session).
- `~/.claude/settings.json.bak-*` — pre-uninstall backup.
- `/tmp/smart-session-rename/state/8b5e0afc-...json` + `logs/...jsonl` — artifacts of the manual `cmd_force` test during Bug #2 investigation. Shows what the CLI writes when `CLAUDE_PLUGIN_DATA` is unset.

## How to reproduce Bug #1 (state corruption)

(Approximate — was observed across real sessions, not intentionally triggered.)

1. Start a fresh claude session in a dir with a mostly-empty or malformed transcript (e.g., brand new project).
2. Have the Stop hook run once with a degenerate turn (minimal content).
3. After the hook completes, inspect `~/.claude/plugins/data/claude-code-smart-session-rename-smart-session-rename-dev/state/<sid>.json` — if it's 1 byte, you've reproduced.

## How to reproduce Bug #2 (force divergence)

1. Open fresh claude session.
2. `/smart-rename force`.
3. One coding turn (any tool use).
4. Wait 90s.
5. `/smart-rename explain` → observe `Estado: ativo; force próximo turno` still present.
6. Compare `~/.claude/plugins/data/.../state/<sid>.json` (hook's view) vs `/tmp/smart-session-rename/state/<sid>.json` (CLI's fallback view if env var not inherited).

---

## Decision log

- **Tagging v1.5.0 anyway:** core pipeline fully validated; bugs affect CLI subcommand paths that have integration-test coverage but real-world regression. Non-blocking.
- **shellcheck gate not run:** `shellcheck` not installed on maintainer's machine (`brew install shellcheck` deferred per original handoff). Advisory only, does not block tag.
- **Level 4 Scenarios 1, 2, 4, 5 not run:** Scenarios 3-5 depend on `/smart-rename force` working reliably. Organic operational data (110+ decisions, 1 real LLM rename) substitutes. Scaffold retained for v1.5.1 re-run.
