# Level 4 Computer Use Scenarios — smart-session-rename v1.5

**Status (2026-04-20):** **Execution aborted mid-Scenario 3** after two non-blocking bugs surfaced that made Scenarios 3-5 unreliable to interpret. Scenarios 1 and 2 logic was manually validated via the operational data in `~/.claude/plugins/data/.../` (3-day organic usage: 110+ `llm_decision` events across 20+ sessions, 1 successful end-to-end rename at $0.6119). Computer Use automation of the workflow was **not exercised**; the manual path was used instead.

Surfaced bugs (deferred to v1.5.1 — see CHANGELOG 1.5.0 § Known issues):
1. Empty-state corruption in Stop hook (state files written as 1 byte).
2. `/smart-rename force` state divergence — CLI and hook may read/write different `CLAUDE_PLUGIN_DATA` directories.

This scaffold is retained for future execution once v1.5.1 lands.

---

**Purpose:** exercise the full skill surface (hook + subcommands + native
`/rename` detection) through a secondary Claude Code session driven by
Computer Use, simulating an end-user who controls titles primarily via
the skill rather than via CLI.

**Budget:** **$10 USD hard cap** (same meter as Phase 9).

---

## Pre-flight

### 1. User enables Computer Use in their **primary** Claude session

*This is done in a fresh Claude Code session separate from the one that
implemented v1.5.* In the primary session:

- Run `/mcp` → find `computer-use` → Enable.
- Grant macOS Accessibility + Screen Recording permissions when prompted.
- Verify: `mcp__computer-use__screenshot` works (take a test screenshot).

The **primary session** (with Computer Use enabled) becomes the
"CU-driving Claude" below. It drives interactions against a **target
Claude Code session** running in a visible terminal window.

### 2. Data path (no export needed)

**Important:** CC overrides `CLAUDE_PLUGIN_DATA` at hook-invocation time. Exporting it in your shell has **no effect**. All plugin state/logs land at:

```bash
export PLUGIN_DATA="$HOME/.claude/plugins/data/claude-code-smart-session-rename-smart-session-rename-dev"
ls "$PLUGIN_DATA"  # logs/ and state/
```

To isolate Level 4 data from prior runs, either (a) record the starting
cumulative cost before scenario 1 and subtract at the end, or (b)
temporarily move the dir aside (`mv "$PLUGIN_DATA"
"$PLUGIN_DATA.pre-level4"`) and let the plugin recreate it on first
hook fire.

### 3. Cost meter (delta-based)

Baseline before scenario 1:

```bash
PLUGIN_DATA="$HOME/.claude/plugins/data/claude-code-smart-session-rename-smart-session-rename-dev"
BASELINE=$(find "$PLUGIN_DATA/logs" -name '*.jsonl' -exec \
  jq -s 'map(select(.event=="llm_call_end")) | map(.cost_usd) | add // 0' {} \; \
  | awk '{s+=$1} END {printf "%.4f", s+0}')
echo "Baseline before Level 4: \$$BASELINE"
```

After each scenario:

```bash
CUR=$(find "$PLUGIN_DATA/logs" -name '*.jsonl' -exec \
  jq -s 'map(select(.event=="llm_call_end")) | map(.cost_usd) | add // 0' {} \; \
  | awk '{s+=$1} END {printf "%.4f", s+0}')
echo "Level 4 delta so far: \$$(echo "$CUR - $BASELINE" | bc) / \$10 cap"
```

**If delta >= $8, STOP and reassess.**

---

## Scenario 1 — Smoke (~5 turns)

**Objective:** verify the CU-driving Claude can reach the skill and that
state file is created.

**Steps (CU-driving Claude executes):**
1. Open a visible terminal window with a target Claude Code session in a
   throwaway project dir.
2. Type `/smart-rename freeze` in the target session.
3. Take a `screenshot` of the terminal.
4. Via Bash: `cat "$CLAUDE_PLUGIN_DATA"/state/*.json`.

**Expected:** state file shows `"freeze": true` (or equivalent) and the
screenshot confirms visual feedback from the skill.

**Record:**
- Target session ID:
- Screenshot confirms `/smart-rename freeze` output: yes / no
- State JSON excerpt showing freeze:
- Notes:

---

## Scenario 2 — Evolution (~10 turns)

**Objective:** watch title evolve across multiple turns and confirm the
title surfaces in the session picker (not just state).

**Steps:**
1. Fresh target session; CU-driving Claude sends 8-10 coding prompts
   (e.g., "add rate limiting", then "now add tests", then "refactor the
   middleware", etc.).
2. After every 2-3 turns, CU-driving Claude inspects state via Bash.
3. At mid-session, CU-driving Claude opens the session picker (⌘K or
   equivalent shortcut for this Claude Code build) and takes a
   `screenshot` confirming the current custom title is visible.

**Expected:**
- 2-4 `calls_made`, title evolves 2-3 times.
- Session picker screenshot shows the latest `rendered_title`.

**Record:**
- Target session ID:
- Title evolution (turn → title):
- Session-picker screenshot confirms title: yes / no
- Picker matches current `rendered_title` from state: yes / no
- Notes:

---

## Scenario 3 — Controls chain

**Objective:** exercise the full subcommand surface in one session.

**Sequence (CU-driving Claude runs each in order, screenshotting between):**
1. `/smart-rename freeze`
2. Two unrelated coding turns (feature work).
3. `/smart-rename explain` → screenshot output.
4. `/smart-rename unfreeze`
5. `/smart-rename force`
6. One coding turn → expected: forced LLM call, `overflow_used` increments
   if budget was at max, otherwise `calls_made` increments.
7. `/smart-rename <new-anchor>` (pick a domain slug like `ci` or `auth`).
8. `/smart-rename explain` → screenshot output.

**Expected:**
- `freeze` pauses auto-rename; explain reflects it.
- `unfreeze` resumes; explain reflects it.
- `force` fires on next hook; overflow/calls adjusts per budget state.
- Anchor locks domain to chosen slug; clauses still evolve.

**Record:**
- Target session ID:
- Freeze state after step 1: (paste `/smart-rename explain` output)
- State after step 4 unfreeze:
- Force consumed (overflow or calls): ______
- Anchor domain after step 7:
- Final `explain` output (step 8):
- Notes / friction points:

---

## Scenario 4 — `/rename` nativo detection

**Objective:** verify that when the user types native `/rename "..."` in
the target session, the hook detects it as `manual_title_override` and
does NOT overwrite it on subsequent turns.

**Steps:**
1. Fresh target session; let auto-rename fire once (so a title exists).
2. CU-driving Claude types native `/rename "My handpicked title"`.
3. Two more coding turns (normally would trigger auto-rename).
4. CU-driving Claude inspects state JSON.

**Expected:**
- `manual_title_override` is `"My handpicked title"` in state.
- `rendered_title` matches `manual_title_override` after steps 3 and 4
  (not replaced by fresh LLM output).

**Record:**
- Target session ID:
- `manual_title_override` value in state:
- `rendered_title` after additional turns: matches override / was overwritten
- Notes:

---

## Scenario 5 (optional) — Circuit breaker

**Objective:** confirm `llm_disabled` trips after 3 real consecutive
failures and that `/smart-rename force` does not bypass it (circuit
breaker is intentionally non-overridable except via `unfreeze` semantics
or state reset).

**Steps:**
1. Fresh target session; disconnect network (Wi-Fi off or use a tool to
   block outbound).
2. Trigger 3 turns that should cross the work-score threshold.
3. Reconnect network.
4. Inspect state; run `/smart-rename explain`.

**Expected:**
- After 3 failures, `failure_count: 3` and `llm_disabled: true`.
- `explain` surfaces circuit-breaker state clearly.

**Skip if:** disconnecting network is too disruptive in the user's
environment. Not blocking for v1.5.0.

**Record (if run):**
- `failure_count`:
- `llm_disabled`:
- `explain` output:

---

## Final tally

- Cumulative cost: $_____ / $10
- Scenarios completed: ___ / 5 (4 required + 1 optional)
- Friction points / UX complaints:
- Threshold-tuning suggestions (feeds Phase 11.1):
  - `first_call_work_threshold`:
  - `ongoing_threshold`:
  - `max_budget_calls`:
  - `circuit_breaker_threshold`:
- Bugs surfaced (file as issues):

---

## Execution log

- [ ] Scenario 1 (smoke) run at: ____________
- [ ] Scenario 2 (evolution) run at: ____________
- [ ] Scenario 3 (controls chain) run at: ____________
- [ ] Scenario 4 (/rename nativo) run at: ____________
- [ ] Scenario 5 (circuit breaker) run at: ____________ (or skipped)
- [ ] Final meter check & tally filled: ____________
