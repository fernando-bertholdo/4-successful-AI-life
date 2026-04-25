# Changelog

## [1.5.0] — 2026-04-18

### Changed (breaking)
- Complete rewrite as modular bash (`scripts/lib/*.sh`). 8 focused modules replace the monolithic v1 scripts.
- Title format is now `domain: clause1, clause2, ...` (was kebab-case).
- Deterministic work-score throttling replaces the fixed 3-message interval.
- Budget model: 6 LLM calls per session + 2 manual overflow slots via `/smart-rename force`.
- State schema version `1.5`. No migration from v1 states (the prior format was transient and not in real use).

### Added
- Structured LLM output via `claude -p --json-schema`; invalid outputs fall back cleanly.
- Seven `/smart-rename` subcommands: `<name>` (anchor), `freeze`, `unfreeze`, `force`, `explain`, `unanchor`, and bare `/smart-rename` (suggest, consumes budget).
- Native `/rename "..."` detection — recorded as `manual_title_override` (free-form, verbatim, never overwritten).
- Distinction between `manual_anchor` (domain slug only, clauses still evolve) and `manual_title_override` (full title, verbatim).
- Circuit breaker after 3 consecutive LLM failures; resettable via `/smart-rename force`.
- JSONL structured logs per session (JSON-safe construction via `jq -nc --arg`).
- Idempotency via `last_processed_signature` (turn_number:file_size) — covers agentic multi-Stop where the hook fires several times within a single user turn.
- Portable timeout wrapper (`timeout` / `gtimeout` / `perl -e alarm`) so `claude -p` always terminates.
- `lock_stale_seconds` raised to 180s (was 30) to accommodate nested `claude -p` cold-starts (~50-90s with cache creation).
- Model guard in `llm.sh`: falls back to `claude-haiku-4-5` if config resolution returns a bogus model value.
- Integration tests (`tests/integration/test-end-to-end.sh`) covering 19 scenarios including writer-failure state non-promotion, circuit breaker, multi-Stop signature idempotency, pivot, and force/overflow.
- Level 3 (real `claude -p`) and Level 4 (Computer Use) manual-test scaffolds under `docs/test-results/` with $10 budget caps.

### Removed
- Fixed 3-message update interval.
- Heuristic kebab-case fallback.
- v1 scripts: `generate-name.sh`, `session-writer.sh`, `utils.sh`, and their paired tests.

### Known limitations
- `writer_append_title` is not atomic under simultaneous hook ↔ skill execution. Both go through `state_lock`, so transcript-level races are very rare in practice, but concurrent writes to the same JSONL are theoretically possible. Acceptable for v1.5; revisit if observed in practice.
- `CLAUDE_PLUGIN_DATA` is injected per-plugin by Claude Code and may point at another plugin's data dir in some environments. The plugin resolves defaults via `BASH_SOURCE` (absolute repo path) instead of relying on `CLAUDE_PLUGIN_DATA`. State/logs may still land in the wrong tree under unusual setups.

### Known issues (deferred to v1.5.1)
Surfaced during Level 3/4 manual testing. Non-blocking for core auto-rename flow (validated: 110+ `llm_decision` events across 20+ organic sessions, 1 successful LLM call + title write in Scenario C at $0.6119). See `docs/superpowers/handoff/2026-04-20-known-issues.md` for investigation notes.

- **Empty-state corruption in Stop hook.** Some state files in `~/.claude/plugins/data/<pluginId>-<marketplaceId>/state/` are 1 byte (just `\n`), suggesting `state_save` was called with an empty `STATE` variable. Root cause is almost certainly a `jq` pipeline in `scripts/rename-hook.sh` failing silently (e.g., when `transcript_parse_current_turn` returns empty, or `--argjson` receives malformed JSON from a bad `TURN` value). Mitigation in place: `state_load` auto-moves corrupted files to `.corrupt.bak` and returns `{}`, so the next hook run recovers from scratch — the only user-visible effect is losing in-flight title evolution for that session. Fix plan for 1.5.1: validate jq output at each mutation point; skip `state_save` when `STATE` is empty and log `state_corruption_prevented`.
- **`/smart-rename force` state divergence.** Observed during Level 4 Scenario 3: after `/smart-rename force`, the CLI writes `force_next=true` via `cmd_force`, but the subsequent Stop hook does not consume the force flag (hook's `state_load` reads a state where `force_next=false`). Hypothesis: Claude Code may not inject `CLAUDE_PLUGIN_DATA` consistently between hook-invocation and skill-invocation (Bash tool) paths, causing `_state_file` to resolve to different directories. When `CLAUDE_PLUGIN_DATA` is unset the default is `/tmp/smart-session-rename/`, a different tree entirely. Fix plan for 1.5.1: pin the data path via a stable helper that checks both CC-managed and legacy locations; emit a `state_path` trace event on every hook/CLI entry to confirm path agreement.
- **Stop-hook runtime registry sticks to first-install state.** `/reload-plugins` does not force a full re-parse of `hooks.json` once the plugin has been enabled. A clean re-registration requires `/plugin uninstall` + `/plugin install` from a fresh CC session. This is a Claude Code harness behavior (not a plugin bug), documented here so future maintainers don't spend hours rediscovering it during local dev iterations.

## [1.0.0] — 2026-03-24

### Added
- Automatic session naming after first meaningful interaction.
- Periodic title updates every N messages (default: 3).
- Title evolution derived from original name.
- On-demand `/smart-rename` skill.
- Configurable via environment variables and config file.
