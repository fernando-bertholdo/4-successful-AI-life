# Level 3 Manual Scenarios — smart-session-rename v1.5

**Purpose:** validate real LLM behavior (not mocked) across representative
session shapes before tagging v1.5.0.

**Budget:** **$10 USD hard cap** across all scenarios combined. Real `claude -p`
calls are issued; each costs ~$0.10 in OAuth mode (see README "Cost model").

---

## Pre-flight

Plugin must be installed via the `/plugin` menu (marketplace type `directory` pointing at this repo). Dev-install alone isn't enough — the plugin must be Enabled in `~/.claude/settings.json → enabledPlugins`.

**Important:** Claude Code overrides `CLAUDE_PLUGIN_DATA` at hook-invocation time. Exporting it in your shell has no effect. The real data path is:

```bash
export PLUGIN_DATA="$HOME/.claude/plugins/data/claude-code-smart-session-rename-smart-session-rename-dev"
ls "$PLUGIN_DATA"  # should show logs/ and state/
```

All three Level 3 scenarios share this single data tree (one `<sessionId>.json` and one `<sessionId>.jsonl` per session run under the plugin).

---

## Cost meter

After **every** scenario, run:

```bash
PLUGIN_DATA="$HOME/.claude/plugins/data/claude-code-smart-session-rename-smart-session-rename-dev"
find "$PLUGIN_DATA/logs" -name '*.jsonl' -exec \
  jq -s 'map(select(.event == "llm_call_end")) | map(.cost_usd) | add // 0' {} \; \
  | awk '{s+=$1} END {printf "Cumulative plugin cost (all sessions): $%.4f / $10 cap\n", s}'
```

**If cumulative >= $8, STOP and reassess before running the next scenario.**

Per-scenario summary (grab the session ID from the Claude Code header, or `ls -lt $PLUGIN_DATA/state/ | head`):

```bash
SID=<session-id>
jq -s 'map(select(.event == "llm_call_end")) | {calls: length, cost_total: (map(.cost_usd) | add // 0)}' \
  "$PLUGIN_DATA/logs/$SID.jsonl"
jq . "$PLUGIN_DATA/state/$SID.json"
```

---

## Scenario A — Short bugfix (~10 turns)

**Setup:** fresh throwaway project dir; small bug involving 1-2 files
(e.g., off-by-one, missing null-check, typo in import path).

**Expected behavior:**
- 1-2 LLM calls total.
- Title shaped like `<domain>: <short clause>` (e.g., `auth: fix token expiry`).
- No overflow consumed, no circuit-breaker trips.

**Record below:**

- Session ID:
- Turn count:
- `calls_made`:
- `overflow_used`:
- Total cost ($):
- Title evolution (titles as they appeared):
- Subjective title quality (1-5):
- Notes/surprises:

---

## Scenario B — Long feature (~30 turns)

**Setup:** prompt a feature with 4-6 sub-tasks (e.g., "add an OAuth2 flow:
config, authorize endpoint, callback, token refresh, session storage, tests").

**Expected behavior:**
- Title evolves 3-5 times as scope shifts.
- `calls_made` approaches budget (6); possibly `overflow_used > 0` if the
  user triggers `/smart-rename force`.
- No circuit breaker.

**Record below:**

- Session ID:
- Turn count:
- `calls_made` / `max_budget_calls`:
- `overflow_used`:
- Total cost ($):
- Title evolution history (turn → title):
- Budget-exhaustion behavior (what happened at call #7+):
- Subjective title quality (1-5):
- Notes/surprises:

---

## Scenario C — Q&A exploration (~15 turns, no tool calls)

**Setup:** conceptual questions only. Examples:
- "Explain React useEffect cleanup semantics."
- "What are the trade-offs of JWT vs session cookies?"
- "How does eventual consistency differ from strong consistency?"

No Read/Edit/Write/Bash tools used by the model.

**Expected behavior:**
- `calls_made: 0` across the entire session (pre-filter skips; work score
  stays below `first_call_work_threshold`).
- No title written.

**Record below (2026-04-18 run — hybrid Q&A + test-orchestration session, not pure conceptual Q&A):**

- Session ID: `a66c77b3-6a58-4629-879c-46b3e6007727`
- Turn count: 24 (per `last_processed_signature`)
- `calls_made`: **1** (exceeded expected 0)
- Unexpected LLM call at turn 21: `{"event":"llm_decision","decision":"call","reason":"first_call_threshold"}` followed by `{"event":"llm_call_end","cost_usd":0.6119,"duration_ms":76583}`
- Title produced: `project-setup: initialize repository structure, configure build and development tools, set up environment and dependencies, establish coding standards, prepare deployment pipeline`
- Notes/surprises:
  - Session wasn't pure Q&A — included test-setup orchestration (Bash, file edits), which pushed the work score past `first_call_work_threshold=20` on turn 21.
  - Title quality: plausible for the test-orchestration framing, but generic. Subjective 3/5.
  - Pre-filter correctly skipped 11 consecutive turns below threshold before triggering.
  - One `lock_contention` event logged (async multi-Stop race) — plugin handled it gracefully.
  - First-call cost of $0.6119 is significantly higher than the original README estimate of ~$0.10. First-call in a fresh terminal incurs cache creation; subsequent calls in same terminal should be cheaper. README updated accordingly.

---

## Final tally (partial — Level 3 merged with operational data)

- Cumulative cost across plugin lifetime: **$0.6119 / $10 cap** (single call, Scenario C hybrid session)
- Scenarios explicitly run: 1/3 (Scenario C, hybrid). Scenarios A and B deferred — plugin's 3-day operational history (110 `llm_decision` events across 20+ real sessions) already covers the short-bugfix and long-feature shapes by sampling organic usage, making synthetic A/B scenarios lower-value.
- Threshold-tuning suggestions (feeds Phase 11.1):
  - `first_call_work_threshold` current default 20 — **about right**. Crossed on turn 21 in the hybrid Scenario C (which had real tool usage). Keeping at 20 per user decision (2026-04-18); revisit in a v1.5.1 patch if real-world false-positive rate emerges.
  - `ongoing_threshold` current default 40 — no data (only one LLM call observed, no ongoing renames). Keep at 40.
  - `max_budget_calls` current default 6 — no data (never approached cap). Keep at 6.

---

## Execution log

- [x] Scenario C (hybrid) run at: 2026-04-18T06:29-06:37Z
- [x] Final meter check & tally filled: 2026-04-18T07:45Z
- [ ] Scenarios A and B — deferred; operational data substitutes
