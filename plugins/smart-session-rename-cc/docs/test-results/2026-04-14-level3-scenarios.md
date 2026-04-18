# Level 3 Manual Scenarios — smart-session-rename v1.5

**Purpose:** validate real LLM behavior (not mocked) across representative
session shapes before tagging v1.5.0.

**Budget:** **$10 USD hard cap** across all scenarios combined. Real `claude -p`
calls are issued; each costs ~$0.10 in OAuth mode (see README "Cost model").

---

## Pre-flight

Plugin must be dev-installed. Set a dedicated data root so all three
scenarios share one log tree and the cost meter below works:

```bash
export CLAUDE_PLUGIN_DATA="$HOME/.local/share/smart-session-rename/level3-$(date +%Y%m%d)"
mkdir -p "$CLAUDE_PLUGIN_DATA"
echo "Level 3 data root: $CLAUDE_PLUGIN_DATA"
```

Export this in every shell where you run a scenario, otherwise logs land
elsewhere and the meter undercounts.

---

## Cost meter

After **every** scenario, run:

```bash
find "$CLAUDE_PLUGIN_DATA/logs" -name '*.jsonl' -exec \
  jq -s 'map(select(.event == "llm_call_end")) | map(.cost_usd) | add // 0' {} \; \
  | awk '{s+=$1} END {printf "Cumulative Level 3 cost: $%.4f / $10 cap\n", s}'
```

**If cumulative >= $8, STOP and reassess before running the next scenario.**

Per-scenario summary:
```bash
SID=<session-id from Claude Code header>
jq -s 'map(select(.event == "llm_call_end")) | {calls: length, cost_total: (map(.cost_usd) | add // 0)}' \
  "$CLAUDE_PLUGIN_DATA/logs/$SID.jsonl"
jq . "$CLAUDE_PLUGIN_DATA/state/$SID.json"
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

**Record below:**

- Session ID:
- Turn count:
- `calls_made` (must be 0):
- Any unexpected LLM calls? If yes, paste the `llm_decision` log line:
- Notes/surprises:

---

## Final tally

- Cumulative cost: $_____ / $10
- Scenarios under budget: ___ / 3
- Threshold-tuning suggestions (feeds Phase 11.1):
  - `first_call_work_threshold` current default 20 — felt: too eager / about right / too conservative
  - `ongoing_threshold` current default 40 — felt: too eager / about right / too conservative
  - `max_budget_calls` current default 6 — felt: too low / about right / too high

---

## Execution log (append timestamps as scenarios are run)

- [ ] Scenario A run at: ____________
- [ ] Scenario B run at: ____________
- [ ] Scenario C run at: ____________
- [ ] Final meter check & tally filled: ____________
