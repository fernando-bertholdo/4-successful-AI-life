# claude-code-smart-session-rename

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Version](https://img.shields.io/badge/version-1.5.0-blue.svg)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Plugin-purple.svg)

**Auto-name your Claude Code sessions. Stop hunting through `quirky-blue-elephant` and `sharp-gifted-tesla`.**

---

## The Problem

You have 47 sessions named `quirky-blue-elephant`, `sharp-gifted-tesla`, and `mild-curious-darwin`. Good luck finding your auth refactor.

Every time you start a new Claude Code session it gets assigned a random three-word identifier. Perfect for throwaway chats, terrible for real work. By the time you've written meaningful code you've forgotten what the session was for.

---

## The Solution

`claude-code-smart-session-rename` watches your conversations and writes a meaningful title to each session based on what you're actually building. It waits until enough substantive work has happened, asks Haiku for a structured `domain: clause1, clause2` title, and writes it back into the transcript so Claude Code's session picker displays it.

- **Deterministic throttling** — a work score decides when it's worth calling the LLM, so the plugin stays quiet during Q&A and chatty only when real code is happening.
- **Evolves with your work** — titles extend as scope grows (`auth: add rate limiting` → `auth: add rate limiting, tests`) and pivot when the subject changes.
- **You remain in control** — seven subcommands under `/smart-rename` let you override, anchor a domain, freeze, force, or inspect.

---

## Quick Start

```bash
claude plugin install claude-code-smart-session-rename
```

Verify the hook is wired:

```
/smart-rename explain
```

You should see the current state snapshot. If that prints, you're done.

---

## How It Works

The Stop hook runs after every assistant turn and walks this pipeline:

1. **Parse input** — `session_id`, `transcript_path`, `cwd` from the hook stdin JSON.
2. **Lock + load state** — per-session JSON at `<data-root>/state/<session_id>.json` under an atomic lock.
3. **Detect native `/rename`** — if the user typed `/rename "..."` natively, capture it as `manual_title_override` (verbatim, never overwritten).
4. **Parse the current turn** — extract tool uses, files touched, user message, assistant summary, branch.
5. **Compute work-score delta** — tool uses, new files, user-msg length; accumulate toward the threshold.
6. **Decide** — `first_call_work_threshold` (default 20) for the first title, `ongoing_work_threshold` (default 40) afterward; signature-based idempotency prevents double-counting under agentic multi-Stop.
7. **Call LLM** — `claude -p --json-schema` with Haiku; validates, renders, and deduplicates clauses.
8. **Write + promote** — append a `custom-title` JSONL record to the transcript; only promote state (title, score reset, transition history) if the write succeeded.

Every step fails closed: missing deps, read-only transcripts, or LLM errors never block your session. Three consecutive LLM failures trip a circuit breaker until `/smart-rename force` resets it.

---

## Cost model

Each LLM call in OAuth mode costs **~$0.10** because `claude -p` loads the full Claude Code context (~80k tokens of cache creation) before running your short prompt. The plugin budgets **6 calls per session** (≈$0.60/session) with **2 manual overflow slots** via `/smart-rename force`.

Using `ANTHROPIC_API_KEY` with a `--bare`-style invocation would reduce cost by roughly 250× but isn't the default in v1.5 because it requires users to manage their own API keys and bypasses Claude Code's native plugin chain. See the design spec §1 for the full trade-off.

---

## Configuration

All settings are read at hook time via `env > file > defaults` precedence. Config file: `<data-root>/config.json` (same tree as state/logs). Defaults are in `config/default-config.json`.

| Env variable | Key | Default | Description |
|---|---|---|---|
| `SMART_RENAME_ENABLED` | `enabled` | `true` | Master switch |
| `SMART_RENAME_MODEL` | `model` | `claude-haiku-4-5` | Model ID for `claude -p --model` |
| `SMART_RENAME_BUDGET_CALLS` | `max_budget_calls` | `6` | Ordinary LLM calls per session |
| `SMART_RENAME_OVERFLOW_SLOTS` | `overflow_manual_slots` | `2` | Extra slots reachable only via `/smart-rename force` |
| `SMART_RENAME_FIRST_THRESHOLD` | `first_call_work_threshold` | `20` | Score needed before the first title |
| `SMART_RENAME_ONGOING_THRESHOLD` | `ongoing_work_threshold` | `40` | Score needed for subsequent updates |
| `SMART_RENAME_REATTACH_INTERVAL` | `reattach_interval` | `10` | Re-append the last title every N turns (robustness) |
| `SMART_RENAME_CB_THRESHOLD` | `circuit_breaker_threshold` | `3` | Consecutive LLM failures that disable the plugin for the session |
| `SMART_RENAME_LOCK_STALE` | `lock_stale_seconds` | `180` | Stale-lock reap threshold |
| `SMART_RENAME_LLM_TIMEOUT` | `llm_timeout_seconds` | `90` | Per-call timeout (`claude -p` typically needs 50-90s) |
| `SMART_RENAME_LOG_LEVEL` | `log_level` | `info` | `debug \| info \| warn \| error` |

Values follow the precedence: a set env var wins, then the config file, then the default.

---

## Subcommands

All seven commands run through the `/smart-rename` skill:

- **`/smart-rename`** — ask the LLM to suggest a title right now. **Consumes one budget slot.** Because it spawns a nested `claude -p`, Claude Code must run this with a timeout of at least 120 seconds (the skill instruction handles that).
- **`/smart-rename <name>`** — set a **domain anchor** (the part before `:`). Clauses still evolve; only the domain is pinned. Good for "I know this is an `auth` session, stop guessing."
- **`/smart-rename freeze`** — pause auto-rename. The current title stays as-is.
- **`/smart-rename unfreeze`** — resume auto-rename.
- **`/smart-rename force`** — run the next Stop hook's LLM call even if the score hasn't crossed the threshold. If the budget is already exhausted, it consumes one of the two overflow slots.
- **`/smart-rename explain`** — print the current state snapshot (title, score, budget, flags).
- **`/smart-rename unanchor`** — clear a domain anchor set earlier.

`/rename "<custom title>"` (native Claude Code command) is detected by the hook and recorded as `manual_title_override`. The plugin then stops fighting you — your title is written verbatim and is never overwritten by LLM output.

---

## FAQ

**Why is there a budget?**
Each `claude -p` invocation costs ~$0.10 in OAuth mode because it recreates the Claude Code prompt cache. Without a budget, a long session would cost several dollars just for titles. Six calls + two overflow slots keeps a typical session under $1.

**How does the plugin decide when to rename?**
A deterministic work score — counting tool uses, newly touched files, and user-message length — accumulates each turn. When it crosses `first_call_work_threshold` (default 20) for the first title or `ongoing_work_threshold` (default 40) afterward, the hook calls Haiku. Pure Q&A turns score near zero, so exploration sessions typically make zero LLM calls.

**What if I want to control the name myself?**
Three options, in increasing strength:
1. `/smart-rename <name>` — pin the domain, let clauses evolve.
2. `/smart-rename freeze` — pause entirely; resume later with `unfreeze`.
3. `/rename "My exact title"` (native) — the plugin records this as an override and never touches the title again.

**Does it ever block my session?**
No. The hook always exits 0, handles every internal failure with `log_event` to a JSONL log, and returns within its 120-second timeout even in the worst case. If the LLM fails three turns in a row, the circuit breaker trips and stays tripped until you run `/smart-rename force`.

**Can I disable it or uninstall?**
`SMART_RENAME_ENABLED=false` pauses the hook without removing the plugin. Or:
```bash
claude plugin uninstall claude-code-smart-session-rename
```
Session titles revert to whatever Claude Code's native auto-namer picks.

---

## Contributing

Found a bug? Have an idea for smarter throttling? PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT

---

**Made for Claude Code users who have better things to do than remember session names.**
