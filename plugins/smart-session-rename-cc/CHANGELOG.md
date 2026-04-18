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

## [1.0.0] — 2026-03-24

### Added
- Automatic session naming after first meaningful interaction.
- Periodic title updates every N messages (default: 3).
- Title evolution derived from original name.
- On-demand `/smart-rename` skill.
- Configurable via environment variables and config file.
