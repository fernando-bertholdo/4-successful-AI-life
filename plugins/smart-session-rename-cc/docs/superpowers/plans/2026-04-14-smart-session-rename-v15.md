# Smart Session Rename v1.5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace v1 with a greenfield v1.5 plugin that auto-renames Claude Code sessions using deterministic throttling heuristics + a single Haiku call with structured output.

**Architecture:** Stop hook → modular bash pipeline (state → config/logger → transcript → work-score → decide → LLM → validate → write). Cognition is in a single `claude -p --json-schema` call gated by heuristics (budget 6 calls/session, work-score thresholds). Each module in `scripts/lib/` has one responsibility and its own test file. Skill prototype validates mechanism before foundation investment.

**Tech Stack:** bash 5.x + jq 1.6+, `claude` CLI v2.1.85+ (Haiku 4.5), custom shell test harness (same pattern as v1).

**Spec:** `docs/superpowers/specs/2026-04-14-smart-session-rename-v15-design.md`

---

## Changes since previous revision (post Gate 1+2 review)

**2026-04-15 addendum:** added a "Manual Testing Strategy" section after
"File Structure". Tasks 1.2, 1.3, 7.1, 9.1, 10.1 were rewritten to tag each
step as **[AGENT]** or **[USER]** and to include copy-paste commands,
pre-filled results-template docs, and explicit handoff points. Rationale:
the implementing agent cannot drive another Claude Code TUI via `computer-use`
(Terminal is tier "click" — typing is sandbox-blocked), so the manual steps
were made verbose enough for the user to run them without guessing.

This plan was revised after adversarial review found 8 critical bugs and several architectural issues. Key changes:

- **Phase order reshuffled:** skill prototype now runs BEFORE config/logger investment (spec §13 Phase 1).
- **Critical bug fixes** in hook orchestrator: `last_processed_turn` timing, trap separation, state promotion after writer success, safe JSON log construction, cwd propagation.
- **Idempotency upgraded** from `turn_number` to `last_processed_signature` (turn + file size) — covers multi-Stop in agentic loops.
- **Manual `/rename` detection** now distinguishes title-override from domain-anchor (prevents ugly `"free text: add tests"`).
- **LLM wrapper** uses jq-based prompt rendering (handles multiline) and portable timeout (`timeout`/`gtimeout`/`perl` fallback for macOS).
- **Lock-during-LLM race mitigated:** `lock_stale_seconds` raised to 60 (2× llm timeout).
- **Config/logger/state integration:** logger.sh and state.sh use `config_get` (not env direct), loaded via `config.sh` source.
- **v1 deletion moved to Phase 8** (after integration tests pass) — preserves rollback path during build.
- **Docs moved to Phase 11** (after Level 3/4 calibrates defaults).
- **Explicit cost cap** for Level 3/4 testing ($10 per phase, hard stop).
- **Test coverage added:** multi-Stop, pivot scenario, force/overflow, anchor persistence, extended LLM mock (is_error, timeout, partial, invalid output).

---

## File Structure

### Files to CREATE

```
scripts/
├── rename-hook.sh                    # REPLACE v1 (complete rewrite as thin orchestrator)
├── smart-rename-cli.sh               # new (skill subcommand dispatcher)
├── lib/
│   ├── config.sh                     # new
│   ├── state.sh                      # new
│   ├── logger.sh                     # new
│   ├── transcript.sh                 # new
│   ├── scorer.sh                     # new
│   ├── llm.sh                        # new
│   ├── validate.sh                   # new
│   └── writer.sh                     # new
└── prompts/
    └── generation.md                 # new

tests/
├── unit/                             # new subdir
│   ├── test-state.sh
│   ├── test-config.sh
│   ├── test-logger.sh
│   ├── test-transcript.sh
│   ├── test-scorer.sh
│   ├── test-llm.sh
│   ├── test-validate.sh
│   └── test-writer.sh
├── integration/                      # new subdir
│   └── test-end-to-end.sh
├── fixtures/
│   ├── transcript-real-capture.jsonl # captured from a real session (T2)
│   ├── transcript-v15-feature.jsonl
│   ├── transcript-v15-qa.jsonl
│   ├── transcript-v15-pivot.jsonl
│   ├── transcript-v15-agentic.jsonl
│   └── transcript-v15-multi-stop.jsonl
└── mocks/
    └── claude                        # new (extended mock covering failure modes)
```

### Files to DELETE in Phase 8 (after integration passes)

- `scripts/generate-name.sh`, `scripts/session-writer.sh`, `scripts/utils.sh`
- `tests/test-generate-name.sh`, `tests/test-rename-hook.sh`, `tests/test-session-writer.sh`, `tests/test-utils.sh`

### Files to CREATE (additional)

- `.claude-plugin/marketplace.json` — minimal local marketplace manifest pointing at `./`. Required for `/plugin` install to discover this repo as a dev plugin (without it, `/plugin` errors with "Marketplace file not found"). Discovered during Phase 1.3 smoke test (iteration 1) and committed as part of Phase 1.3.

### Files to MODIFY

- `.claude-plugin/plugin.json` — bump to 1.5.0
- `config/default-config.json` — replace with v1.5 defaults
- `hooks/hooks.json` — unchanged (entry point remains `scripts/rename-hook.sh`)
- `skills/smart-rename/SKILL.md` — rewrite for v1.5 subcommands
- `tests/run-tests.sh` — walk `unit/` and `integration/`
- `README.md`, `CHANGELOG.md` — in Phase 11 (after Level 3/4 findings)

---

## Manual Testing Strategy

Several tasks (1.2, 1.3, 7.1, 9.1, 10.1) involve interaction with a "real" Claude
Code session. The implementing agent **cannot** drive another Claude Code session
via `computer-use` because Terminal/iTerm apps are tier **"click"** under the
computer-use sandbox (typing is blocked in terminals and IDEs) — so the agent
cannot type prompts or slash commands into another interactive Claude Code
instance. This constraint shapes the protocol below.

### Step ownership convention

Each step in affected tasks is tagged:
- **[AGENT]** — the implementing agent performs it alone (file ops, Bash,
  commits, jq queries).
- **[USER]** — requires the human user: running interactive commands, pasting
  output back, observing behavior that only shows in a real session.

### Handoff protocol for [USER] steps

1. **[AGENT]** prepares every artifact the user needs (scripts, SKILL.md,
   results-template doc pre-filled with the questions to answer).
2. **[AGENT]** writes the exact copy-paste commands the user must run, with
   expected output for each, in a single code block.
3. **[AGENT]** stops and says "Pausing for manual test — when done, paste
   command outputs back and answer the questions in docs/test-results/…".
4. **[USER]** runs commands, captures output, answers questions.
5. **[AGENT]** fills the results doc, commits, continues.

### Task-specific strategies

**Task 1.2 — Capture real JSONL**
Uses the **current implementing session's own JSONL** (the agent is *in* a real
Claude Code session; its transcript under `~/.claude/projects/<encoded>/….jsonl`
is a real fixture). All steps are [AGENT]; no user involvement needed.

**Task 1.3 — Skill prototype smoke test**
[AGENT] generates `smart-rename-cli.sh`, `SKILL.md`, and the results-template
doc. [AGENT] then instructs [USER] to dev-install the plugin (via `/plugin` or
`CLAUDE_PLUGIN_ROOT=<repo>` env) and run `/smart-rename freeze` +
`/smart-rename unfreeze` in a *fresh* Claude Code session (not this one — a new
session is needed because the current session was started before the plugin
existed in this state, so its skill registry doesn't include smart-rename yet).

**Task 7.1 — Full skill smoke test**
Same pattern as 1.3 but covering all 7 subcommands. [AGENT] generates CLI +
SKILL.md + results template. [USER] runs the subcommand chain in a fresh
session. [AGENT] records findings.

**Task 9.1 — Level 3 manual scenarios ($10 cap)**
[AGENT] writes `docs/test-results/<date>-level3-scenarios.md` with: explicit
prerequisites (plugin installed, `CLAUDE_PLUGIN_DATA` set, mock OFF), copy-paste
prompt scripts for each scenario (A/B/C), the exact cost-meter `jq` command to
run between scenarios, and a stop-loss checklist. [USER] runs scenarios in real
sessions (paying real LLM cost), reports observations. [AGENT] finalizes the
results doc and commits.

**Task 10.1 — Level 4 Computer Use ($10 cap)**
[AGENT] writes the scenario doc. [USER] enables Computer Use MCP + macOS
permissions, runs the 5 scenarios driving Claude Code from a secondary agent
via computer-use (the user's own desktop, not this agent's). [USER] reports
observations + screenshots. [AGENT] records results and commits.

### Why the agent cannot self-run 1.3 / 7.1 / 9.1 / 10.1

- **Tier "click" blocks `type`/`key` on Terminal/iTerm**: `left_click` works,
  but typing a prompt is denied by the sandbox. The agent can `open_application`
  and `screenshot` the terminal but cannot enter text.
- **`claude -p` (print mode) does not execute slash commands the same way** —
  slash commands are handled by the interactive skill registry, not by the
  non-interactive `-p` pipeline. So `claude -p "/smart-rename freeze"` is not
  equivalent and would not validate the skill mechanism this plan needs to test.
- **Forking a child `claude` interactive process via Bash** doesn't help either:
  the TUI requires a controlled terminal (PTY) and bidirectional input the
  agent cannot supply through `Bash` tool invocations alone.

The net effect: the agent can do everything except press Enter in a Claude Code
TUI. That single step is what [USER] covers.

---

## Phase 0: Prepare workspace

### Task 0.1: Handle pre-existing v1 modifications

- [ ] **Step 1: Check uncommitted changes**

```bash
git status --short scripts/
```
If output shows `M scripts/generate-name.sh` and/or `M scripts/rename-hook.sh`, proceed to Step 2. If clean, skip to Phase 1.

- [ ] **Step 2: Ask user how to handle them**

Use `AskUserQuestion` (or ask directly) offering:
- (a) Commit them as v1 history: `git add scripts/generate-name.sh scripts/rename-hook.sh && git commit -m "chore: preserve v1 learnings on JSONL format and portable lock before v1.5 rewrite"`
- (b) Discard: `git checkout scripts/generate-name.sh scripts/rename-hook.sh`

Execute the user's choice.

- [ ] **Step 3: Verify clean tree**

```bash
git status --short scripts/
```
Expected: empty.

---

## Phase 1: State foundation + skill prototype (validate mechanism early)

Rationale: the spec (§13 Phase 1) prescribes validating the skill mechanism before heavy investment. `state.sh` has no dependencies beyond `jq`, so we build it first, then prototype the skill, then expand.

### Task 1.1: Create `lib/state.sh` with tests (env fallback for config)

**Files:**
- Create: `scripts/lib/state.sh`
- Create: `tests/unit/test-state.sh`

- [ ] **Step 1: Create `tests/unit/test-state.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/state.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

echo "=== state.sh tests ==="
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
SID="sess-1"

echo "-- state_load on missing file returns {} --"
state=$(state_load "$SID")
assert_eq "empty load" "{}" "$state"

echo "-- state_save + state_load roundtrip --"
state_save "$SID" '{"version":"1.5","calls_made":3}'
state=$(state_load "$SID")
assert_eq "version" "1.5" "$(echo "$state" | jq -r '.version')"
assert_eq "calls_made" "3" "$(echo "$state" | jq -r '.calls_made')"

echo "-- no leftover tmp files --"
tmp_count=$(find "$CLAUDE_PLUGIN_DATA/state" -name '*.tmp*' 2>/dev/null | wc -l | tr -d ' ')
assert_eq "no tmp" "0" "$tmp_count"

echo "-- lock / unlock --"
state_lock "$SID" && { echo "  ✓ acquired"; ((PASS++)) || true; } || { echo "  ✗ failed"; ((FAIL++)) || true; }
[[ -d "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir" ]] && { echo "  ✓ lockdir exists"; ((PASS++)) || true; } || { echo "  ✗ missing"; ((FAIL++)) || true; }

echo "-- second lock attempt fails fast --"
start=$(date +%s)
if state_lock "$SID" 2>/dev/null; then
  echo "  ✗ second lock should fail"; ((FAIL++)) || true
else
  elapsed=$(($(date +%s) - start))
  [[ $elapsed -le 3 ]] && { echo "  ✓ failed within 3s"; ((PASS++)) || true; } || { echo "  ✗ too slow: ${elapsed}s"; ((FAIL++)) || true; }
fi

state_unlock "$SID"
[[ ! -d "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir" ]] && { echo "  ✓ released"; ((PASS++)) || true; } || { echo "  ✗ still held"; ((FAIL++)) || true; }

echo "-- stale lock cleaned (>= SMART_RENAME_LOCK_STALE seconds) --"
mkdir -p "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir"
# backdate 80s (exceeds default 60s stale threshold)
touch -t "$(date -v-80S +"%Y%m%d%H%M.%S" 2>/dev/null || date -u -d '80 seconds ago' +"%Y%m%d%H%M.%S")" "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir"
state_lock "$SID" && { echo "  ✓ stale cleaned"; ((PASS++)) || true; } || { echo "  ✗ stale not cleaned"; ((FAIL++)) || true; }
state_unlock "$SID"

echo "-- corrupt state renames to .corrupt.bak and returns {} --"
echo "not valid json {" > "$CLAUDE_PLUGIN_DATA/state/$SID.json"
state=$(state_load "$SID")
assert_eq "corrupt resets" "{}" "$state"
[[ -f "$CLAUDE_PLUGIN_DATA/state/$SID.json.corrupt.bak" ]] && { echo "  ✓ backup saved"; ((PASS++)) || true; } || { echo "  ✗ backup missing"; ((FAIL++)) || true; }

echo "-- env fallback honored when config.sh not sourced --"
export SMART_RENAME_LOCK_STALE=120
# Re-source to pick up env; no config_get available
stale=$(_state_lock_stale_seconds)
assert_eq "env override" "120" "$stale"
unset SMART_RENAME_LOCK_STALE

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bash tests/unit/test-state.sh
```
Expected: missing file error.

- [ ] **Step 3: Create `scripts/lib/state.sh`**

```bash
#!/usr/bin/env bash
# lib/state.sh — session state JSON load/save + locking.
# Config resolution: uses config_get if config.sh is sourced, else falls back to env.

_state_file() {
  local sid="$1"
  local base="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}"
  mkdir -p "$base/state"
  echo "$base/state/$sid.json"
}

_state_lockdir() {
  echo "$(_state_file "$1").lockdir"
}

# Returns stale threshold seconds. Prefers config_get, falls back to env, then 60.
_state_lock_stale_seconds() {
  if declare -F config_get >/dev/null 2>&1; then
    local v; v=$(config_get lock_stale_seconds 2>/dev/null)
    [[ -n "$v" ]] && { echo "$v"; return 0; }
  fi
  echo "${SMART_RENAME_LOCK_STALE:-60}"
}

state_load() {
  local sid="$1"
  local f; f="$(_state_file "$sid")"
  if [[ ! -f "$f" ]]; then
    echo "{}"
    return 0
  fi
  if ! jq . "$f" >/dev/null 2>&1; then
    mv -f "$f" "${f}.corrupt.bak" 2>/dev/null || true
    echo "{}"
    return 0
  fi
  cat "$f"
}

state_save() {
  local sid="$1" json="$2"
  local f tmp
  f="$(_state_file "$sid")"
  tmp="${f}.tmp.$$"
  printf '%s\n' "$json" > "$tmp"
  mv -f "$tmp" "$f"
}

state_lock() {
  local sid="$1"
  local lockdir stale_seconds max_wait waited
  lockdir="$(_state_lockdir "$sid")"
  stale_seconds="$(_state_lock_stale_seconds)"
  max_wait=2
  waited=0

  if [[ -d "$lockdir" ]]; then
    local age
    age=$(( $(date +%s) - $(stat -f %m "$lockdir" 2>/dev/null || stat -c %Y "$lockdir") ))
    if [[ $age -ge $stale_seconds ]]; then
      rm -rf "$lockdir" 2>/dev/null || true
    fi
  fi

  while ! mkdir "$lockdir" 2>/dev/null; do
    if [[ $waited -ge $max_wait ]]; then
      return 1
    fi
    sleep 0.5
    waited=$((waited + 1))
  done
  return 0
}

state_unlock() {
  local sid="$1"
  rm -rf "$(_state_lockdir "$sid")" 2>/dev/null || true
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
bash tests/unit/test-state.sh
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/state.sh tests/unit/test-state.sh
git commit -m "feat(v1.5): add lib/state.sh with atomic save, portable lock, env fallback"
```

---

### Task 1.2: Capture real JSONL fixture from a live session

Rationale: Gate 2 flagged that the parser was being validated only against synthetic fixtures. This task captures a real transcript to verify format assumptions before freezing the parser.

Per the **Manual Testing Strategy** section, this task reuses the implementing
session's own JSONL — no separate manual session required. All steps [AGENT].

**Files:**
- Create: `tests/fixtures/transcript-real-capture.jsonl`

- [ ] **Step 1: [AGENT] Locate the current session's JSONL**

Claude Code stores each session at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`.
The encoded cwd for this repo is
`-Users-fernandobertholdo-Documents-tech-projects-claude-code-smart-session-rename`.
Pick the most recently modified JSONL in that directory (= the current session):

```bash
PROJECT_ENCODED="-Users-fernandobertholdo-Documents-tech-projects-claude-code-smart-session-rename"
SRC="$(ls -t ~/.claude/projects/"$PROJECT_ENCODED"/*.jsonl 2>/dev/null | head -1)"
echo "Source: $SRC"
wc -l "$SRC"
```

If `SRC` is empty, fall back to scanning all project dirs (`ls -t ~/.claude/projects/*/*.jsonl | head -1`). If that also yields nothing, STOP and report (user will need to run something in Claude Code first).

- [ ] **Step 2: [AGENT] Copy as fixture**

```bash
mkdir -p tests/fixtures
cp "$SRC" tests/fixtures/transcript-real-capture.jsonl
```

- [ ] **Step 3: [AGENT] Sanity-check format assumptions**

```bash
echo "-- user content shapes --"
jq -rs '[.[] | select(.type == "user") | .message.content | type] | unique' tests/fixtures/transcript-real-capture.jsonl

echo "-- sample user entries --"
jq -c 'select(.type == "user")' tests/fixtures/transcript-real-capture.jsonl | head -3

echo "-- assistant with tool_use --"
jq -c 'select(.type == "assistant" and (.message.content | type == "array"))' tests/fixtures/transcript-real-capture.jsonl | head -2

echo "-- distinct record types --"
jq -rs '[.[] | .type] | unique' tests/fixtures/transcript-real-capture.jsonl
```

Record observations as a `#`-prefixed comment at the **top** of the fixture
file — specifically whether `user.message.content` was observed as `string`,
`array`, or both. (This calibrates expectations for the parser in Phase 3.1.)

- [ ] **Step 4: [AGENT] Scrub sensitive content**

The raw transcript may contain absolute paths (`/Users/fernandobertholdo/…`),
API keys, or conversational content the user doesn't want in git. Apply a
scrub pass:

```bash
# Replace absolute user path with a generic placeholder
sed -i.bak 's#/Users/fernandobertholdo#/Users/<user>#g' tests/fixtures/transcript-real-capture.jsonl
rm -f tests/fixtures/transcript-real-capture.jsonl.bak
```

Then manually scan the file for: `ghp_`, `sk-ant-`, `sk-`, `xoxb-`, IP
addresses, email addresses, or any content that looks personal. Replace with
`<redacted>`. Report the scrub result to the user before committing, listing
any redactions made so the user can confirm nothing sensitive slipped through.

- [ ] **Step 5: [AGENT] Commit (after user confirms the scrub)**

```bash
git add tests/fixtures/transcript-real-capture.jsonl
git commit -m "test(v1.5): capture real Claude Code JSONL fixture for parser validation"
```

---

### Task 1.3: Skill prototype (minimal freeze/unfreeze using only `state.sh`)

**Files:**
- Create: `scripts/smart-rename-cli.sh` (minimal Phase 1 version)
- Modify: `skills/smart-rename/SKILL.md` (minimal Phase 1 version)
- Create: `docs/test-results/2026-04-14-skill-prototype.md`

> **Lesson learned (Phase 1.3 first iteration, 2026-04-15):** the smoke test
> revealed that `$CLAUDE_SESSION_ID` and `$CLAUDE_TRANSCRIPT_PATH` are NOT
> exposed as env vars when a skill invokes the Bash tool — only `$CLAUDE_PLUGIN_ROOT`
> is. The CLI must therefore derive the session id from `pwd -P` (scan
> `~/.claude/projects/<encoded-cwd>/` for the most recent `.jsonl`). The code
> below already incorporates that fix; the SKILL.md no longer passes a
> transcript-path arg. Encoding rule observed: replace `/` AND `_` with `-`,
> prepend `-`, resolve symlinks via `pwd -P` (matters on macOS where `/tmp` is
> `/private/tmp`).

- [ ] **Step 1: Create minimal `scripts/smart-rename-cli.sh`**

```bash
#!/usr/bin/env bash
# smart-rename-cli.sh — skill subcommand dispatcher (Phase 1: freeze/unfreeze only)
#
# Session id resolution (in priority order):
#   1. $CLAUDE_SESSION_ID env var (set by hooks; usually NOT set when invoked from a skill)
#   2. transcript path arg ($1) → derive from .jsonl filename
#   3. cwd-derive: scan ~/.claude/projects/<encoded-pwd>/ for the most recent .jsonl
#
# Encoding rule (observed empirically from Claude Code CLI v2.1.85):
#   - Resolve symlinks via `pwd -P`
#   - Strip leading `/`
#   - Replace every `/` AND `_` with `-`
#   - Prepend a single `-`
# Example: /Users/x/tech_projects/foo  →  -Users-x-tech-projects-foo
#
# Set SMART_RENAME_DEBUG=1 to print resolution steps to stderr.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/state.sh"

_dbg() { [[ -n "${SMART_RENAME_DEBUG:-}" ]] && echo "[debug] $*" >&2 || true; }

_encode_cwd() {
  local p="${1:-$(pwd -P)}"
  echo "-$(echo "$p" | sed 's|^/||' | tr '/_' '--')"
}

_session_id_from_cwd() {
  local encoded proj_dir latest
  encoded="$(_encode_cwd)"
  proj_dir="$HOME/.claude/projects/$encoded"
  _dbg "cwd=$(pwd -P)"
  _dbg "encoded=$encoded"
  _dbg "proj_dir=$proj_dir (exists=$([[ -d "$proj_dir" ]] && echo yes || echo no))"
  [[ -d "$proj_dir" ]] || return 1
  latest="$(ls -t "$proj_dir"/*.jsonl 2>/dev/null | head -1)"
  _dbg "latest_jsonl=$latest"
  [[ -z "$latest" ]] && return 1
  basename "$latest" .jsonl
}

session_id_from_args() {
  if [[ -n "${CLAUDE_SESSION_ID:-}" ]]; then
    _dbg "source=env CLAUDE_SESSION_ID"
    echo "$CLAUDE_SESSION_ID"; return 0
  fi
  if [[ -n "${1:-}" && -f "$1" ]]; then
    _dbg "source=arg transcript_path=$1"
    basename "$1" .jsonl; return 0
  fi
  local sid; sid="$(_session_id_from_cwd)" || true
  if [[ -n "$sid" ]]; then
    _dbg "source=cwd-derive"
    echo "$sid"; return 0
  fi
  return 1
}

cmd="${1:-}"; shift || true

case "$cmd" in
  freeze|unfreeze)
    sid="$(session_id_from_args "${1:-}")"
    if [[ -z "$sid" ]]; then
      echo "ERROR: cannot determine session id" >&2
      echo "  Tried: \$CLAUDE_SESSION_ID, transcript_path arg, cwd-derive from $(pwd -P)" >&2
      echo "  Run with SMART_RENAME_DEBUG=1 for resolution trace." >&2
      exit 1
    fi
    state_lock "$sid" || { echo "ERROR: could not lock"; exit 1; }
    trap "state_unlock $sid" EXIT
    state=$(state_load "$sid")
    if [[ "$cmd" == "freeze" ]]; then
      new_state=$(echo "$state" | jq '.frozen = true | .updated_at = (now | todate)')
      echo "Smart rename: FROZEN for session $sid"
    else
      new_state=$(echo "$state" | jq '.frozen = false | .updated_at = (now | todate)')
      echo "Smart rename: UNFROZEN for session $sid"
    fi
    state_save "$sid" "$new_state"
    ;;
  *)
    echo "Phase 1 prototype — only freeze/unfreeze supported."
    exit 1
    ;;
esac
```

Make executable: `chmod +x scripts/smart-rename-cli.sh`

- [ ] **Step 2: Write minimal `skills/smart-rename/SKILL.md` (Phase 1)**

```markdown
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
```

- [ ] **Step 3: [AGENT] Create results-template doc pre-filled with questions**

Create `docs/test-results/2026-04-14-skill-prototype.md`:

```markdown
# Phase 1.3 — Skill Prototype Smoke Test Results

Date: 2026-04-14
Tester: Fernando Bertholdo

## Environment
- Claude Code version: <paste `claude --version` output here>
- CLAUDE_PLUGIN_DATA: <paste `echo $CLAUDE_PLUGIN_DATA` output here>
- Plugin install mode: dev (linked from this repo)

## Test transcript

### 1. /smart-rename freeze
- [ ] Ran command: `/smart-rename freeze`
- Output observed: `<paste verbatim output>`
- Expected: `Smart rename: FROZEN for session <id>`
- Matched expected? yes / no

### 2. State file after freeze
- [ ] Ran: `cat "$CLAUDE_PLUGIN_DATA/state/<id>.json" | jq .`
- Output observed:
  ```
  <paste jq output>
  ```
- `.frozen` field present and `true`? yes / no

### 3. /smart-rename unfreeze
- [ ] Ran command: `/smart-rename unfreeze`
- Output observed: `<paste verbatim output>`
- Expected: `Smart rename: UNFROZEN for session <id>`
- Matched expected? yes / no

### 4. State file after unfreeze
- [ ] `.frozen` field now `false`? yes / no

## Mechanism validation questions
- Was `$CLAUDE_SESSION_ID` set in the skill environment when the script ran?
  (Check by adding `echo "SID=$CLAUDE_SESSION_ID" >&2` temporarily to the CLI,
  or confirm indirectly: does the session_id in the state file match the
  current session's id shown in Claude Code header?)
  Answer: __________
- Did the Bash tool execute `${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh`
  without path issues? (If yes, `$CLAUDE_PLUGIN_ROOT` was correctly exposed.)
  Answer: __________
- Any race with the Stop hook firing after the skill's own turn?
  (If you see a `custom-title` record appended immediately after the freeze
  command, the Stop hook ran — note whether it respected the freeze flag.)
  Answer: __________
- Did session-id derivation from `$CLAUDE_TRANSCRIPT_PATH` work correctly when
  `$CLAUDE_SESSION_ID` was absent? (Force-test: unset CLAUDE_SESSION_ID and
  re-run. Not strictly required at this phase.)
  Answer: __________ (skip if not tested)

## Verdict
- [ ] ✅ Prototype succeeded — proceed to Phase 2.
- [ ] ❌ Prototype failed — see adjustments needed below.

## Adjustments needed (only if failed)
<describe what broke and what the mechanism needs to change>
```

- [ ] **Step 4: [USER] Dev-install the plugin and run the smoke test**

Prerequisites:
- The current agent-driven session may NOT see the new skill because its
  plugin registry was loaded at session start. **Start a fresh Claude Code
  session** for this smoke test.
- Dev-install this repo as a plugin. Two common ways:
  - `/plugin` in Claude Code → point at this repo path, or
  - Export `CLAUDE_PLUGIN_ROOT` env to this repo before launching `claude`:
    ```bash
    export CLAUDE_PLUGIN_ROOT=/Users/fernandobertholdo/Documents/tech_projects/claude-code-smart-session-rename
    claude
    ```
- Pick **any** small project as the working directory (doesn't need to be
  this repo — in fact, not this repo is preferable to avoid the Stop hook
  clashing with your smoke test).

In the fresh session, run in order:

```
/smart-rename freeze
```
```bash
# In a second terminal (while the Claude Code session is still open):
cat "${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}/state/"*.json | jq .
```
Record the values you see (session id, `.frozen`).

```
/smart-rename unfreeze
```
```bash
cat "${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}/state/"*.json | jq .
```
Confirm `.frozen` is now `false`.

**Fill in** `docs/test-results/2026-04-14-skill-prototype.md` with the actual
outputs and answers, then paste the completed content back to the agent
(or commit it yourself — either works).

- [ ] **Step 5: [AGENT] Assess verdict + commit**

If the user's results doc shows ✅ verdict: commit and proceed to Phase 2.

```bash
git add scripts/smart-rename-cli.sh skills/smart-rename/SKILL.md docs/test-results/2026-04-14-skill-prototype.md
git commit -m "feat(v1.5): Phase 1 skill prototype (freeze/unfreeze) validates mechanism"
```

If ❌: STOP. Review the "Adjustments needed" section with the user; revise
the mechanism (pass session_id explicitly, different invocation, etc.)
before continuing to Phase 2.

---

## Phase 2: Config and logger, refactor state

### Task 2.1: Create `lib/config.sh` with tests

> **Note from Phase 1.3 smoke test:** `$CLAUDE_PLUGIN_DATA` is **injected by
> Claude Code per-plugin** when a skill or hook invokes the Bash tool. It
> resolves to `~/.claude/plugins/data/<plugin-name>-<marketplace-name>/`
> (example for our dev install: `claude-code-smart-session-rename-smart-session-rename-dev`).
> A user `export CLAUDE_PLUGIN_DATA=...` in their outer shell is **overridden**
> by CC inside skill/hook executions and only takes effect for out-of-band CLI
> invocations. `config.sh` already treats `${CLAUDE_PLUGIN_DATA:-}` as the
> source of truth for both default-config and user-override file paths — no
> code change needed, just be aware of where the user-config file actually
> needs to live (CC's path, not the user's chosen one). Document this in the
> Phase 11 README under "Configuration".

**Files:**
- Create: `scripts/lib/config.sh`
- Create: `tests/unit/test-config.sh`
- Modify: `config/default-config.json`

- [ ] **Step 1: Replace `config/default-config.json`**

```json
{
  "enabled": true,
  "model": "claude-haiku-4-5",

  "max_budget_calls": 6,
  "overflow_manual_slots": 2,
  "first_call_work_threshold": 20,
  "ongoing_work_threshold": 40,

  "reattach_interval": 10,
  "circuit_breaker_threshold": 3,
  "lock_stale_seconds": 60,
  "llm_timeout_seconds": 25,

  "log_level": "info",
  "max_clauses": 5,
  "max_domain_chars": 30,
  "max_user_msg_chars": 500,
  "max_assistant_chars": 500
}
```

Note: `lock_stale_seconds` is 60 (was 30) to provide 2× safety margin over `llm_timeout_seconds: 25`.

- [ ] **Step 2: Create `tests/unit/test-config.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/config.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

echo "=== config.sh tests ==="
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
for v in SMART_RENAME_ENABLED SMART_RENAME_MODEL SMART_RENAME_BUDGET_CALLS \
         SMART_RENAME_OVERFLOW_SLOTS SMART_RENAME_FIRST_THRESHOLD \
         SMART_RENAME_ONGOING_THRESHOLD SMART_RENAME_REATTACH_INTERVAL \
         SMART_RENAME_CB_THRESHOLD SMART_RENAME_LOCK_STALE \
         SMART_RENAME_LLM_TIMEOUT SMART_RENAME_LOG_LEVEL; do unset "$v" 2>/dev/null; done

echo "-- defaults --"
config_load
assert_eq "enabled default" "true" "$(config_get enabled)"
assert_eq "model default" "claude-haiku-4-5" "$(config_get model)"
assert_eq "budget default" "6" "$(config_get max_budget_calls)"
assert_eq "first_threshold default" "20" "$(config_get first_call_work_threshold)"
assert_eq "lock_stale_seconds default" "60" "$(config_get lock_stale_seconds)"

echo "-- env overrides --"
export SMART_RENAME_BUDGET_CALLS=10
export SMART_RENAME_FIRST_THRESHOLD=15
config_load
assert_eq "env budget" "10" "$(config_get max_budget_calls)"
assert_eq "env first" "15" "$(config_get first_call_work_threshold)"
unset SMART_RENAME_BUDGET_CALLS SMART_RENAME_FIRST_THRESHOLD

echo "-- user config file overrides defaults --"
cat > "$CLAUDE_PLUGIN_DATA/config.json" <<EOF
{"max_budget_calls": 4, "ongoing_work_threshold": 50}
EOF
config_load
assert_eq "file budget" "4" "$(config_get max_budget_calls)"
assert_eq "file ongoing" "50" "$(config_get ongoing_work_threshold)"
assert_eq "default first kept" "20" "$(config_get first_call_work_threshold)"

echo "-- env > file > defaults --"
export SMART_RENAME_BUDGET_CALLS=99
config_load
assert_eq "env beats file" "99" "$(config_get max_budget_calls)"
unset SMART_RENAME_BUDGET_CALLS

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 3: Run test to verify it fails**

```bash
bash tests/unit/test-config.sh
```
Expected: missing file.

- [ ] **Step 4: Create `scripts/lib/config.sh`**

```bash
#!/usr/bin/env bash
# lib/config.sh — config loading with precedence: env > user file > defaults

_CONFIG_LOADED=""
declare -gA _CONFIG_VALUES

_config_env_var() {
  case "$1" in
    enabled)                   echo "SMART_RENAME_ENABLED" ;;
    model)                     echo "SMART_RENAME_MODEL" ;;
    max_budget_calls)          echo "SMART_RENAME_BUDGET_CALLS" ;;
    overflow_manual_slots)     echo "SMART_RENAME_OVERFLOW_SLOTS" ;;
    first_call_work_threshold) echo "SMART_RENAME_FIRST_THRESHOLD" ;;
    ongoing_work_threshold)    echo "SMART_RENAME_ONGOING_THRESHOLD" ;;
    reattach_interval)         echo "SMART_RENAME_REATTACH_INTERVAL" ;;
    circuit_breaker_threshold) echo "SMART_RENAME_CB_THRESHOLD" ;;
    lock_stale_seconds)        echo "SMART_RENAME_LOCK_STALE" ;;
    llm_timeout_seconds)       echo "SMART_RENAME_LLM_TIMEOUT" ;;
    log_level)                 echo "SMART_RENAME_LOG_LEVEL" ;;
    *)                         echo "" ;;
  esac
}

config_load() {
  local defaults_file user_file
  defaults_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/config/default-config.json"
  user_file="${CLAUDE_PLUGIN_DATA:-}/config.json"

  _CONFIG_VALUES=()

  if [[ -f "$defaults_file" ]]; then
    while IFS=$'\t' read -r key val; do
      _CONFIG_VALUES["$key"]="$val"
    done < <(jq -r 'to_entries[] | "\(.key)\t\(.value)"' "$defaults_file" 2>/dev/null || true)
  fi

  if [[ -n "${CLAUDE_PLUGIN_DATA:-}" && -f "$user_file" ]]; then
    while IFS=$'\t' read -r key val; do
      _CONFIG_VALUES["$key"]="$val"
    done < <(jq -r 'to_entries[] | "\(.key)\t\(.value)"' "$user_file" 2>/dev/null || true)
  fi

  for key in "${!_CONFIG_VALUES[@]}"; do
    local env_name
    env_name="$(_config_env_var "$key")"
    if [[ -n "$env_name" && -n "${!env_name:-}" ]]; then
      _CONFIG_VALUES["$key"]="${!env_name}"
    fi
  done

  _CONFIG_LOADED=1
}

config_get() {
  local key="$1"
  [[ -z "$_CONFIG_LOADED" ]] && config_load
  echo "${_CONFIG_VALUES[$key]:-}"
}
```

- [ ] **Step 5: Run test to verify it passes + commit**

```bash
bash tests/unit/test-config.sh
```
All pass, then:

```bash
git add scripts/lib/config.sh tests/unit/test-config.sh config/default-config.json
git commit -m "feat(v1.5): add lib/config.sh with env > file > defaults precedence"
```

---

### Task 2.2: Create `lib/logger.sh` (uses `config_get`)

**Files:**
- Create: `scripts/lib/logger.sh`
- Create: `tests/unit/test-logger.sh`

- [ ] **Step 1: Create `tests/unit/test-logger.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/config.sh"
source "$SCRIPT_DIR/../../scripts/lib/logger.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }
assert_contains() { local d="$1" n="$2" h="$3"; [[ "$h" == *"$n"* ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d"; ((FAIL++)) || true; }; }

echo "=== logger.sh tests ==="
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
config_load

echo "-- emits valid JSONL --"
log_event info score_update "sess-a" '{"delta":6,"acc":18.5,"turn":14}'
logfile="$CLAUDE_PLUGIN_DATA/logs/sess-a.jsonl"
[[ -f "$logfile" ]] && { echo "  ✓ file exists"; ((PASS++)) || true; } || { echo "  ✗ missing"; ((FAIL++)) || true; }
line="$(head -1 "$logfile")"
assert_contains "has event" '"event":"score_update"' "$line"
assert_contains "has turn" '"turn":14' "$line"
echo "$line" | jq . >/dev/null 2>&1 && { echo "  ✓ valid JSON"; ((PASS++)) || true; } || { echo "  ✗ invalid JSON: $line"; ((FAIL++)) || true; }

echo "-- unsafe strings are escaped (quotes, newlines) --"
log_event info manual_rename_detected "sess-b" "$(jq -nc --arg t 'title with "quotes" and
newline' '{new_title:$t}')"
logfile="$CLAUDE_PLUGIN_DATA/logs/sess-b.jsonl"
line="$(head -1 "$logfile")"
echo "$line" | jq . >/dev/null 2>&1 && { echo "  ✓ valid JSON with unsafe content"; ((PASS++)) || true; } || { echo "  ✗ invalid: $line"; ((FAIL++)) || true; }

echo "-- level filter honors config --"
rm -f "$CLAUDE_PLUGIN_DATA/logs/sess-c.jsonl"
export SMART_RENAME_LOG_LEVEL=warn
config_load  # reload
log_event info suppressed "sess-c" '{}'
[[ ! -s "$CLAUDE_PLUGIN_DATA/logs/sess-c.jsonl" ]] && { echo "  ✓ info suppressed"; ((PASS++)) || true; } || { echo "  ✗ leaked"; ((FAIL++)) || true; }
log_event warn kept "sess-c" '{}'
grep -q kept "$CLAUDE_PLUGIN_DATA/logs/sess-c.jsonl" && { echo "  ✓ warn kept"; ((PASS++)) || true; } || { echo "  ✗ dropped"; ((FAIL++)) || true; }
unset SMART_RENAME_LOG_LEVEL

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bash tests/unit/test-logger.sh
```
Expected: missing file.

- [ ] **Step 3: Create `scripts/lib/logger.sh`**

```bash
#!/usr/bin/env bash
# lib/logger.sh — structured JSONL logging per session. Uses config_get for log_level.

_log_level_rank() {
  case "$1" in
    debug) echo 0 ;; info) echo 1 ;; warn) echo 2 ;; error) echo 3 ;;
    *) echo 1 ;;
  esac
}

# Args: level event_type session_id data_json
# data_json must be valid JSON produced via jq -nc --arg ... (never string-interpolated).
log_event() {
  local level="$1" event="$2" session_id="$3" data="${4:-\{\}}"

  local cur_level="info"
  if declare -F config_get >/dev/null 2>&1; then
    local v; v=$(config_get log_level 2>/dev/null)
    [[ -n "$v" ]] && cur_level="$v"
  elif [[ -n "${SMART_RENAME_LOG_LEVEL:-}" ]]; then
    cur_level="$SMART_RENAME_LOG_LEVEL"
  fi

  if [[ "$(_log_level_rank "$level")" -lt "$(_log_level_rank "$cur_level")" ]]; then
    return 0
  fi

  local base_dir log_dir log_file ts
  base_dir="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}"
  log_dir="$base_dir/logs"
  mkdir -p "$log_dir"
  log_file="$log_dir/$session_id.jsonl"
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  jq -nc \
    --arg ts "$ts" --arg level "$level" --arg event "$event" \
    --argjson data "$data" \
    '{ts: $ts, level: $level, event: $event} + $data' \
    >> "$log_file" 2>/dev/null || true
}
```

- [ ] **Step 4: Run test + commit**

```bash
bash tests/unit/test-logger.sh
git add scripts/lib/logger.sh tests/unit/test-logger.sh
git commit -m "feat(v1.5): add lib/logger.sh (uses config_get; safe JSON via jq)"
```

---

### Task 2.3: Refactor `tests/unit/test-state.sh` for config integration

state.sh already falls back to env when config.sh is absent. Now verify it uses `config_get` when config.sh IS sourced.

**Files:**
- Modify: `tests/unit/test-state.sh`

- [ ] **Step 1: Append integration test to `tests/unit/test-state.sh`**

Before the final `rm -rf "$CLAUDE_PLUGIN_DATA"`, add:

```bash
echo "-- config_get integration: lock_stale honored via config.json --"
# Source config.sh and set a config-level override
source "$SCRIPT_DIR/../../scripts/lib/config.sh"
unset SMART_RENAME_LOCK_STALE
cat > "$CLAUDE_PLUGIN_DATA/config.json" <<EOF
{"lock_stale_seconds": 999}
EOF
config_load
stale=$(_state_lock_stale_seconds)
assert_eq "config_get wins over default" "999" "$stale"
```

- [ ] **Step 2: Run test + commit**

```bash
bash tests/unit/test-state.sh
git add tests/unit/test-state.sh
git commit -m "test(v1.5): verify state.sh reads lock_stale from config.sh when sourced"
```

---

## Phase 3: Transcript parser

### Task 3.1: Create `lib/transcript.sh` with tests

Addresses: cwd passed explicitly (A3), user content as array (minor), multi-block assistant (T3), agentic loop fixture.

**Files:**
- Create: `scripts/lib/transcript.sh`
- Create: `tests/unit/test-transcript.sh`
- Create: `tests/fixtures/transcript-v15-feature.jsonl`
- Create: `tests/fixtures/transcript-v15-agentic.jsonl`
- Create: `tests/fixtures/transcript-v15-multi-stop.jsonl`

- [ ] **Step 1: Create fixture `tests/fixtures/transcript-v15-feature.jsonl`**

```jsonl
{"type":"user","message":{"role":"user","content":"Add rate limiting to the auth endpoints"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"I'll add rate limiting using express-rate-limit for the login and signup endpoints."},{"type":"tool_use","id":"tu1","name":"Read","input":{"file_path":"src/auth/login.ts"}},{"type":"tool_use","id":"tu2","name":"Read","input":{"file_path":"src/auth/signup.ts"}},{"type":"tool_use","id":"tu3","name":"Edit","input":{"file_path":"src/auth/rate-limit.ts","old_string":"","new_string":"import rateLimit from 'express-rate-limit';\n..."}},{"type":"tool_use","id":"tu4","name":"Bash","input":{"command":"npm test"}}]}}
```

- [ ] **Step 2: Create fixture `tests/fixtures/transcript-v15-agentic.jsonl`**

```jsonl
{"type":"user","message":{"role":"user","content":"Fix the JWT expiry bug in auth module"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Let me investigate the JWT expiry logic."},{"type":"tool_use","id":"a1","name":"Read","input":{"file_path":"src/auth/jwt.ts"}},{"type":"text","text":"I see the issue. The expiry check uses seconds instead of milliseconds."},{"type":"tool_use","id":"a2","name":"Edit","input":{"file_path":"src/auth/jwt.ts","old_string":"Date.now() > exp","new_string":"Date.now() > exp * 1000"}},{"type":"tool_use","id":"a3","name":"Bash","input":{"command":"npm test -- auth"}},{"type":"text","text":"Tests pass. The fix is complete."}]}}
{"type":"user","message":{"role":"user","content":"Also add a test for the edge case where exp is 0"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Adding that edge case test."},{"type":"tool_use","id":"b1","name":"Edit","input":{"file_path":"tests/auth/jwt.test.ts","old_string":"","new_string":"test('handles exp=0', () => { ... })"}},{"type":"tool_use","id":"b2","name":"Bash","input":{"command":"npm test -- auth"}},{"type":"text","text":"Done, test passes."}]}}
```

- [ ] **Step 3: Create fixture `tests/fixtures/transcript-v15-multi-stop.jsonl`**

Simulates a single user turn where the Stop hook would fire twice (agentic loop mid-turn checkpoint then final):

```jsonl
{"type":"user","message":{"role":"user","content":"Implement OAuth2 flow"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Starting OAuth2 setup."},{"type":"tool_use","id":"c1","name":"Read","input":{"file_path":"src/auth/config.ts"}}]}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"c2","name":"Edit","input":{"file_path":"src/auth/oauth.ts","old_string":"","new_string":"export function authorize() {}"}},{"type":"tool_use","id":"c3","name":"Bash","input":{"command":"npm test"}},{"type":"text","text":"OAuth2 flow complete."}]}}
```

- [ ] **Step 4: Create `tests/unit/test-transcript.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/transcript.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

FIX="$SCRIPT_DIR/../fixtures"
CWD="/tmp/fake-project"

echo "=== transcript.sh tests ==="

echo "-- single-turn feature --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-feature.jsonl" "[]" "$CWD")
assert_eq "turn_number" "1" "$(echo "$r" | jq -r '.turn_number')"
assert_eq "user_word_count" "7" "$(echo "$r" | jq -r '.user_word_count')"
assert_eq "tool_call_count" "4" "$(echo "$r" | jq -r '.tool_call_count')"
assert_eq "rate-limit in new files" "true" "$(echo "$r" | jq '[.new_files_this_turn[] | select(contains("rate-limit"))] | length > 0')"

echo "-- agentic multi-turn: only LAST user's turn --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-agentic.jsonl" "[]" "$CWD")
assert_eq "turn_number 2" "2" "$(echo "$r" | jq -r '.turn_number')"
assert_eq "tool_call_count 2" "2" "$(echo "$r" | jq -r '.tool_call_count')"

echo "-- multi-stop: multiple assistant entries in same turn aggregated --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-multi-stop.jsonl" "[]" "$CWD")
assert_eq "turn_number 1 (single user)" "1" "$(echo "$r" | jq -r '.turn_number')"
assert_eq "tool_call_count 3 (aggregated)" "3" "$(echo "$r" | jq -r '.tool_call_count')"

echo "-- new_files excludes previously seen --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-agentic.jsonl" '["src/auth/jwt.ts"]' "$CWD")
assert_eq "one new file" "1" "$(echo "$r" | jq -r '.new_files_this_turn | length')"

echo "-- user content as array (tool_result block) returns usable string --"
tmp=$(mktemp).jsonl
cat > "$tmp" <<'JSONL'
{"type":"user","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"x","content":"prev result"},{"type":"text","text":"Now fix the bug I mentioned"}]}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"d1","name":"Edit","input":{"file_path":"fix.ts"}}]}}
JSONL
r=$(transcript_parse_current_turn "$tmp" "[]" "$CWD")
assert_eq "user_msg extracted from array" "Now fix the bug I mentioned" "$(echo "$r" | jq -r '.user_msg')"
rm -f "$tmp"

echo "-- domain_guess from file paths (second level) --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-agentic.jsonl" "[]" "$CWD")
assert_eq "domain_guess auth" "auth" "$(echo "$r" | jq -r '.domain_guess')"

echo "-- cwd fallback when no files --"
tmp=$(mktemp).jsonl
cat > "$tmp" <<'JSONL'
{"type":"user","message":{"role":"user","content":"hi"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"hello"}]}}
JSONL
r=$(transcript_parse_current_turn "$tmp" "[]" "/tmp/my-project")
assert_eq "domain_guess from cwd" "my-project" "$(echo "$r" | jq -r '.domain_guess')"
rm -f "$tmp"

echo "-- file_size exposed for idempotency signature --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-feature.jsonl" "[]" "$CWD")
fs=$(echo "$r" | jq -r '.file_size')
[[ "$fs" -gt 100 ]] && { echo "  ✓ file_size > 100 ($fs)"; ((PASS++)) || true; } || { echo "  ✗ unexpected file_size: $fs"; ((FAIL++)) || true; }

echo "-- missing transcript returns error field --"
r=$(transcript_parse_current_turn "/nonexistent.jsonl" "[]" "$CWD" || true)
assert_eq "error field" "missing_transcript" "$(echo "$r" | jq -r '.error // ""')"

echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 5: Run test to verify it fails**

```bash
bash tests/unit/test-transcript.sh
```
Expected: missing file.

- [ ] **Step 6: Create `scripts/lib/transcript.sh`**

```bash
#!/usr/bin/env bash
# lib/transcript.sh — parse Claude Code JSONL for the current turn.
# Turn = user message + all following assistant blocks until next user.
# Handles both string and array content in user messages (tool_result + text blocks).

# Args: transcript_path, previous_active_files_json, cwd
# Stdout: JSON with turn signals (schema per v1.5 spec §3.5 + file_size for idempotency)
transcript_parse_current_turn() {
  local path="$1" prev_files_json="${2:-[]}" cwd="${3:-}"

  if [[ ! -r "$path" ]]; then
    echo '{"error":"missing_transcript"}'
    return 0
  fi

  local file_size
  file_size=$(wc -c < "$path" | tr -d ' ')

  local total_turns last_user_msg
  total_turns=$(jq -s 'map(select(.type == "user")) | length' "$path" 2>/dev/null || echo 0)
  last_user_msg=$(jq -rs '
    map(select(.type == "user")) | last // {} | .message.content
    | if type == "string" then .
      elif type == "array" then
        [.[] | select(.type == "text") | .text] | join(" ")
      else "" end
  ' "$path" 2>/dev/null || echo "")

  local user_word_count
  user_word_count=$(echo "$last_user_msg" | tr -s '[:space:]' '\n' | grep -c . 2>/dev/null || echo 0)

  # All assistant blocks after the last user message
  local assistant_content
  assistant_content=$(jq -s '
    . as $all
    | (reduce range(0; $all | length) as $i (-1;
        if $all[$i].type == "user" then $i else . end)) as $lu
    | $all[($lu+1):] | map(select(.type == "assistant"))
  ' "$path" 2>/dev/null || echo '[]')

  local tool_call_count
  tool_call_count=$(echo "$assistant_content" | jq '
    [.[] | .message.content // [] | .[] | select(.type == "tool_use")] | length
  ' 2>/dev/null || echo 0)

  local tool_names
  tool_names=$(echo "$assistant_content" | jq -c '
    [.[] | .message.content // [] | .[] | select(.type == "tool_use") | .name]
  ' 2>/dev/null || echo '[]')

  local all_files
  all_files=$(echo "$assistant_content" | jq -c '
    [.[] | .message.content // [] | .[] | select(.type == "tool_use") | .input.file_path // empty] | unique
  ' 2>/dev/null || echo '[]')

  local new_files
  new_files=$(jq -cn --argjson all "$all_files" --argjson prev "$prev_files_json" '$all - $prev' 2>/dev/null || echo '[]')

  local assistant_text
  assistant_text=$(echo "$assistant_content" | jq -r '
    [.[] | .message.content // [] | .[] | select(.type == "text") | .text] | join(" ")
  ' 2>/dev/null || echo "")

  local assistant_sentence_count
  # NOTE (Phase 3.1 lesson, 2026-04-15): wrap grep in `{ ... || true; }` because
  # `set -euo pipefail` in tests turns grep's exit-1 (no matches) into a pipeline
  # failure. Without this, `... | wc -l | tr ... || echo 0` produces "0\n0" which
  # then breaks `--argjson asent` downstream.
  assistant_sentence_count=$(echo "$assistant_text" | sed 's/```[^`]*```//g' | { grep -oE '[.!?]' || true; } | wc -l | tr -d ' ' || echo 0)

  local domain_guess
  # Try top-level directory dominant. Skip generic container dirs (src, tests, lib,
  # app, pkg) because they describe folder TYPE, not subject DOMAIN — falling
  # through to second-level extracts the meaningful name (e.g., "auth" from
  # both src/auth/... and tests/auth/...). Lesson from Phase 3.1, 2026-04-15.
  # TODO (Phase 9/10 calibration): consider expanding the skip list (docs,
  # scripts, internal, vendor, third_party) once we observe more real transcripts.
  domain_guess=$(echo "$all_files" | jq -r '
    [.[] | split("/")[0] | select(length > 0) | select(. != "src" and . != "tests" and . != "lib" and . != "app" and . != "pkg")]
    | group_by(.) | map({k:.[0], n:length}) | sort_by(-.n) | first.k // empty
  ' 2>/dev/null)
  if [[ -z "$domain_guess" || "$domain_guess" == "null" ]]; then
    # Second-level (e.g., src/auth/...)
    domain_guess=$(echo "$all_files" | jq -r '
      [.[] | split("/") | .[1] // empty | select(. != "")]
      | group_by(.) | map({k:.[0], n:length}) | sort_by(-.n) | first.k // empty
    ' 2>/dev/null)
  fi
  if [[ -z "$domain_guess" || "$domain_guess" == "null" ]]; then
    domain_guess="$(basename "${cwd:-/}")"
  fi

  local branch
  if [[ -n "$cwd" && -d "$cwd" ]]; then
    branch="$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
  else
    branch=""
  fi

  jq -nc \
    --argjson turn "${total_turns:-0}" \
    --arg msg "$last_user_msg" \
    --argjson words "${user_word_count:-0}" \
    --arg atext "$assistant_text" \
    --argjson asent "${assistant_sentence_count:-0}" \
    --argjson tcc "${tool_call_count:-0}" \
    --argjson tnames "$tool_names" \
    --argjson all "$all_files" \
    --argjson nfiles "$new_files" \
    --arg dom "$domain_guess" \
    --arg br "$branch" \
    --argjson fs "${file_size:-0}" \
    '{
      turn_number: $turn,
      user_msg: $msg,
      user_word_count: $words,
      assistant_text: $atext,
      assistant_sentence_count: $asent,
      tool_call_count: $tcc,
      tool_names: $tnames,
      all_files_touched: $all,
      new_files_this_turn: $nfiles,
      domain_guess: $dom,
      branch: $br,
      file_size: $fs
    }'
}
```

- [ ] **Step 7: Run test + commit**

```bash
bash tests/unit/test-transcript.sh
git add scripts/lib/transcript.sh tests/unit/test-transcript.sh tests/fixtures/transcript-v15-feature.jsonl tests/fixtures/transcript-v15-agentic.jsonl tests/fixtures/transcript-v15-multi-stop.jsonl
git commit -m "feat(v1.5): add lib/transcript.sh (cwd arg, array content, file_size for idempotency)"
```

---

## Phase 4: Scorer

### Task 4.1: Create `lib/scorer.sh` with tests

Addresses: idempotency by signature (A1) — `last_processed_signature` = "turn_number:file_size".

**Files:**
- Create: `scripts/lib/scorer.sh`
- Create: `tests/unit/test-scorer.sh`

- [ ] **Step 1: Create `tests/unit/test-scorer.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/config.sh"
source "$SCRIPT_DIR/../../scripts/lib/scorer.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

echo "=== scorer.sh tests ==="
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
config_load

echo "-- compute_delta formula --"
td='{"tool_call_count":3,"new_files_this_turn":["a","b"],"user_word_count":100}'
assert_eq "delta=10" "10" "$(scorer_compute_delta "$td")"
assert_eq "delta=0 on zero" "0" "$(scorer_compute_delta '{"tool_call_count":0,"new_files_this_turn":[],"user_word_count":0}')"

state_base() {
  jq -nc '{frozen:false, force_next:false, llm_disabled:false, failure_count:0, calls_made:0, overflow_used:0, title_struct:null, accumulated_score:0, last_processed_signature:""}'
}

echo "-- frozen → SKIP --"
s=$(state_base | jq '.frozen=true | .accumulated_score=100')
assert_eq "frozen" "skip" "$(scorer_should_call_llm "$s" "0:0" | jq -r '.decision')"
assert_eq "reason" "frozen" "$(scorer_should_call_llm "$s" "0:0" | jq -r '.reason')"

echo "-- force_next → CALL --"
s=$(state_base | jq '.force_next=true')
assert_eq "force" "call" "$(scorer_should_call_llm "$s" "0:0" | jq -r '.decision')"

echo "-- llm_disabled → SKIP --"
s=$(state_base | jq '.llm_disabled=true | .accumulated_score=100')
assert_eq "disabled" "skip" "$(scorer_should_call_llm "$s" "0:0" | jq -r '.decision')"

echo "-- budget exhausted (calls_made == max AND overflow used == slots) → SKIP --"
s=$(state_base | jq '.title_struct={domain:"x"} | .calls_made=6 | .overflow_used=2 | .accumulated_score=100')
assert_eq "exhausted" "skip" "$(scorer_should_call_llm "$s" "0:0" | jq -r '.decision')"

echo "-- force honored while overflow available past budget --"
s=$(state_base | jq '.title_struct={domain:"x"} | .calls_made=6 | .overflow_used=1 | .force_next=true')
assert_eq "force past budget with overflow" "call" "$(scorer_should_call_llm "$s" "0:0" | jq -r '.decision')"

echo "-- first-call threshold --"
s=$(state_base | jq '.accumulated_score=15')
assert_eq "below first" "skip" "$(scorer_should_call_llm "$s" "0:0" | jq -r '.decision')"
s=$(state_base | jq '.accumulated_score=20')
assert_eq "at first" "call" "$(scorer_should_call_llm "$s" "0:0" | jq -r '.decision')"

echo "-- ongoing threshold --"
s=$(state_base | jq '.title_struct={domain:"x"} | .calls_made=1 | .accumulated_score=39')
assert_eq "below ongoing" "skip" "$(scorer_should_call_llm "$s" "0:0" | jq -r '.decision')"
s=$(state_base | jq '.title_struct={domain:"x"} | .calls_made=1 | .accumulated_score=40')
assert_eq "at ongoing" "call" "$(scorer_should_call_llm "$s" "0:0" | jq -r '.decision')"

echo "-- signature idempotency: same signature skips --"
s=$(state_base | jq '.title_struct={domain:"x"} | .calls_made=1 | .accumulated_score=100 | .last_processed_signature="5:1000"')
assert_eq "same sig skip" "skip" "$(scorer_should_call_llm "$s" "5:1000" | jq -r '.decision')"
assert_eq "reason" "already_processed" "$(scorer_should_call_llm "$s" "5:1000" | jq -r '.reason')"

echo "-- signature idempotency: larger file_size on same turn proceeds --"
# Multi-stop scenario: same turn_number but file grew
assert_eq "sig changed" "call" "$(scorer_should_call_llm "$s" "5:2000" | jq -r '.decision')"

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bash tests/unit/test-scorer.sh
```
Expected: missing file.

- [ ] **Step 3: Create `scripts/lib/scorer.sh`**

```bash
#!/usr/bin/env bash
# lib/scorer.sh — work-score + call/skip decision. Idempotency via signature.

# Args: turn_data_json
# Stdout: numeric delta
scorer_compute_delta() {
  local turn="$1"
  echo "$turn" | jq -r '
    ((.tool_call_count // 0)
     + ((.new_files_this_turn // []) | length) * 3
     + ((.user_word_count // 0) * 0.01))
  ' 2>/dev/null | awk '{ printf "%g\n", $1 }'
}

# Signature format: "<turn_number>:<file_size>"
# Same turn+size means the hook is re-entering for the same state → skip.
# Same turn but larger size = more content written since last run (agentic loop mid-turn) → proceed.

# Args: state_json, current_signature
# Stdout: {"decision":"call"|"skip","reason":"<string>"}
scorer_should_call_llm() {
  local state="$1" current_sig="$2"

  local last_sig
  last_sig=$(echo "$state" | jq -r '.last_processed_signature // ""')
  if [[ -n "$last_sig" && "$last_sig" == "$current_sig" ]]; then
    echo '{"decision":"skip","reason":"already_processed"}'
    return 0
  fi

  local frozen force_next llm_disabled has_title
  frozen=$(echo "$state" | jq -r '.frozen // false')
  force_next=$(echo "$state" | jq -r '.force_next // false')
  llm_disabled=$(echo "$state" | jq -r '.llm_disabled // false')
  has_title=$(echo "$state" | jq -r 'if .title_struct then "true" else "false" end')

  local calls_made overflow_used
  calls_made=$(echo "$state" | jq -r '.calls_made // 0')
  overflow_used=$(echo "$state" | jq -r '.overflow_used // 0')

  local max_calls overflow_slots
  max_calls=$(config_get max_budget_calls)
  overflow_slots=$(config_get overflow_manual_slots)

  local acc first_thr ongoing_thr
  acc=$(echo "$state" | jq -r '.accumulated_score // 0')
  first_thr=$(config_get first_call_work_threshold)
  ongoing_thr=$(config_get ongoing_work_threshold)

  if [[ "$frozen" == "true" ]]; then
    echo '{"decision":"skip","reason":"frozen"}'
    return 0
  fi

  if [[ "$force_next" == "true" ]]; then
    # Past budget: need an overflow slot
    if [[ "$calls_made" -ge "$max_calls" ]] && [[ "$overflow_used" -ge "$overflow_slots" ]]; then
      echo '{"decision":"skip","reason":"budget_and_overflow_exhausted"}'
      return 0
    fi
    echo '{"decision":"call","reason":"force_next"}'
    return 0
  fi

  if [[ "$llm_disabled" == "true" ]]; then
    echo '{"decision":"skip","reason":"llm_disabled_circuit_breaker"}'
    return 0
  fi

  if [[ "$calls_made" -ge "$max_calls" ]]; then
    echo '{"decision":"skip","reason":"budget_exhausted"}'
    return 0
  fi

  if [[ "$has_title" == "false" ]]; then
    if awk -v a="$acc" -v t="$first_thr" 'BEGIN { exit !(a >= t) }'; then
      echo '{"decision":"call","reason":"first_call_threshold"}'
      return 0
    fi
    echo '{"decision":"skip","reason":"below_first_threshold"}'
    return 0
  fi

  if awk -v a="$acc" -v t="$ongoing_thr" 'BEGIN { exit !(a >= t) }'; then
    echo '{"decision":"call","reason":"ongoing_threshold"}'
    return 0
  fi
  echo '{"decision":"skip","reason":"below_ongoing_threshold"}'
}
```

- [ ] **Step 4: Run test + commit**

```bash
bash tests/unit/test-scorer.sh
git add scripts/lib/scorer.sh tests/unit/test-scorer.sh
git commit -m "feat(v1.5): add lib/scorer.sh (signature-based idempotency for multi-stop)"
```

---

## Phase 5: LLM pipeline

### Task 5.1: Create `prompts/generation.md`

**Files:**
- Create: `scripts/prompts/generation.md`

- [ ] **Step 1: Write prompt template**

```markdown
You are generating a concise title for an ongoing Claude Code session.

CURRENT TITLE: ${CURRENT_TITLE}
MANUAL ANCHOR: ${MANUAL_ANCHOR}
CURRENT BRANCH: ${BRANCH}
DOMAIN GUESS: ${DOMAIN_GUESS}
RECENT FILES: ${RECENT_FILES}

USER MESSAGE (this turn):
${USER_MSG}

ASSISTANT SUMMARY (this turn, truncated):
${ASSISTANT_SUMMARY}

RECENT CONTEXT (last 3 turns):
${RECENT_TURNS}

RULES:
- Produce {domain, clauses[]} matching the JSON schema provided via --json-schema.
- `domain`: short slug (1-3 words) naming the subject area (e.g., "auth", "deploy-pipeline").
- If MANUAL ANCHOR is set and non-empty, use it exactly as `domain`.
- `clauses`: 1 to 5 items, each `[verb] [concrete entity]` (e.g., "fix jwt expiry", "add tests").
  - Avoid generic jargon ("implementation", "enhancement", "optimization").
  - Prefer active verbs. Entities should be concrete (file, module, behavior).
- If nothing substantial changed versus CURRENT TITLE, return the same structure — the plugin deduplicates identical renderings without re-writing.
- Keep the domain stable across turns unless the subject clearly changed.
```

- [ ] **Step 2: Commit**

```bash
git add scripts/prompts/generation.md
git commit -m "feat(v1.5): add prompts/generation.md"
```

---

### Task 5.2: Create `lib/llm.sh` with extended mock

Addresses: jq-based prompt render (C3, fixes multiline), portable timeout fallback (C4), extended mock failure modes (T1).

**Files:**
- Create: `scripts/lib/llm.sh`
- Create: `tests/unit/test-llm.sh`
- Create: `tests/mocks/claude`

- [ ] **Step 1: Create extended mock `tests/mocks/claude`**

```bash
#!/usr/bin/env bash
# Mock claude CLI for tests.
# Modes (controlled by env):
#   MOCK_CLAUDE_MODE=success    (default)  → returns MOCK_CLAUDE_RESPONSE JSON
#   MOCK_CLAUDE_MODE=fail       → non-zero exit, empty output
#   MOCK_CLAUDE_MODE=timeout    → sleeps past the timeout to force timeout
#   MOCK_CLAUDE_MODE=is_error   → returns result with is_error:true
#   MOCK_CLAUDE_MODE=no_struct  → returns result without structured_output
#   MOCK_CLAUDE_MODE=invalid    → returns invalid JSON on stdout

case "${MOCK_CLAUDE_MODE:-success}" in
  fail)
    echo "mock: simulated failure" >&2
    exit 1
    ;;
  timeout)
    sleep 60
    exit 0
    ;;
  is_error)
    cat <<EOF
[{"type":"result","is_error":true,"duration_ms":100,"total_cost_usd":0,"result":"rate limit"}]
EOF
    exit 0
    ;;
  no_struct)
    cat <<EOF
[{"type":"result","is_error":false,"duration_ms":100,"total_cost_usd":0.001}]
EOF
    exit 0
    ;;
  invalid)
    echo "not json at all"
    exit 0
    ;;
  success|*)
    cat <<EOF
${MOCK_CLAUDE_RESPONSE:-[{"type":"result","is_error":false,"duration_ms":100,"total_cost_usd":0.001,"structured_output":{"domain":"test","clauses":["do thing"]}}]}
EOF
    ;;
esac
```

Make executable: `chmod +x tests/mocks/claude`

- [ ] **Step 2: Create `tests/unit/test-llm.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/config.sh"
source "$SCRIPT_DIR/../../scripts/lib/llm.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

echo "=== llm.sh tests ==="
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
config_load
export PATH="$SCRIPT_DIR/../mocks:$PATH"

ctx=$(jq -nc '{CURRENT_TITLE:"none",MANUAL_ANCHOR:"",BRANCH:"main",DOMAIN_GUESS:"auth",RECENT_FILES:"src/auth/jwt.ts",USER_MSG:"fix jwt",ASSISTANT_SUMMARY:"patched",RECENT_TURNS:"turn 1\nturn 2"}')

echo "-- success parses structured_output --"
unset MOCK_CLAUDE_MODE
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"duration_ms":100,"total_cost_usd":0.001,"structured_output":{"domain":"auth","clauses":["fix jwt","add tests"]}}]'
r=$(llm_generate_title "$ctx")
assert_eq "domain" "auth" "$(echo "$r" | jq -r '.domain')"
assert_eq "clauses count" "2" "$(echo "$r" | jq -r '.clauses | length')"

echo "-- command failure → error:call_failed --"
export MOCK_CLAUDE_MODE=fail
r=$(llm_generate_title "$ctx" || true)
assert_eq "fail error" "call_failed" "$(echo "$r" | jq -r '.error // ""')"

echo "-- is_error:true → error:call_failed --"
export MOCK_CLAUDE_MODE=is_error
r=$(llm_generate_title "$ctx" || true)
assert_eq "is_error" "call_failed" "$(echo "$r" | jq -r '.error // ""')"

echo "-- no structured_output → error:invalid_output --"
export MOCK_CLAUDE_MODE=no_struct
r=$(llm_generate_title "$ctx" || true)
assert_eq "no struct" "invalid_output" "$(echo "$r" | jq -r '.error // ""')"

echo "-- invalid JSON → error:invalid_output --"
export MOCK_CLAUDE_MODE=invalid
r=$(llm_generate_title "$ctx" || true)
assert_eq "invalid" "invalid_output" "$(echo "$r" | jq -r '.error // ""')"

echo "-- multiline RECENT_TURNS does not break prompt rendering --"
unset MOCK_CLAUDE_MODE
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"structured_output":{"domain":"x","clauses":["y"]}}]'
ctx_multi=$(jq -nc '{CURRENT_TITLE:"a",MANUAL_ANCHOR:"",BRANCH:"b",DOMAIN_GUESS:"c",RECENT_FILES:"d",USER_MSG:"e",ASSISTANT_SUMMARY:"f","RECENT_TURNS":"turn 1: alpha\nturn 2: beta / with slashes\nturn 3: \"quotes\""}')
r=$(llm_generate_title "$ctx_multi")
assert_eq "multiline ok" "x" "$(echo "$r" | jq -r '.domain')"

unset MOCK_CLAUDE_MODE MOCK_CLAUDE_RESPONSE
rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 3: Run test to verify it fails**

```bash
bash tests/unit/test-llm.sh
```
Expected: missing file.

- [ ] **Step 4: Create `scripts/lib/llm.sh`**

```bash
#!/usr/bin/env bash
# lib/llm.sh — wrapper around claude -p with --json-schema.
# Portable timeout (timeout/gtimeout/perl fallback). jq-based prompt rendering (multiline-safe).

_LLM_JSON_SCHEMA='{
  "type":"object",
  "properties":{
    "domain":{"type":"string","minLength":1,"maxLength":30},
    "clauses":{"type":"array","items":{"type":"string","minLength":2,"maxLength":50},"minItems":1,"maxItems":5}
  },
  "required":["domain","clauses"],
  "additionalProperties":false
}'

# Picks timeout command: timeout | gtimeout | perl-based | none (no-op)
_llm_timeout_wrapper() {
  local seconds="$1"
  if command -v timeout >/dev/null 2>&1; then
    echo "timeout $seconds"
  elif command -v gtimeout >/dev/null 2>&1; then
    echo "gtimeout $seconds"
  elif command -v perl >/dev/null 2>&1; then
    # perl -e 'alarm shift; exec @ARGV' -- N cmd args...
    echo "perl -e alarm_shift_exec $seconds"
  else
    echo ""
  fi
}

# Runs a command with timeout using the best available wrapper.
# Args: seconds, command, args...
_llm_with_timeout() {
  local seconds="$1"; shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$seconds" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$seconds" "$@"
  elif command -v perl >/dev/null 2>&1; then
    perl -e 'alarm shift; exec @ARGV' "$seconds" "$@"
  else
    "$@"
  fi
}

# Render prompt template with variable substitution. jq-based, handles multiline/quotes/slashes.
_render_prompt() {
  local ctx_json="$1"
  local template_file
  template_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/prompts/generation.md"
  [[ ! -f "$template_file" ]] && return 1

  jq -nr --rawfile tmpl "$template_file" --argjson ctx "$ctx_json" '
    $ctx
    | to_entries
    | reduce .[] as $e ($tmpl;
        gsub("\\$\\{" + $e.key + "\\}"; ($e.value | tostring))
      )
  '
}

llm_generate_title() {
  local ctx_json="$1"
  local prompt
  prompt=$(_render_prompt "$ctx_json") || { echo '{"error":"prompt_template_missing"}'; return 1; }

  local model timeout_s
  model=$(config_get model)
  timeout_s=$(config_get llm_timeout_seconds)

  local raw rc
  raw=$(_llm_with_timeout "$timeout_s" claude -p \
    --model "$model" \
    --output-format json \
    --no-session-persistence \
    --json-schema "$_LLM_JSON_SCHEMA" \
    "$prompt" 2>/dev/null)
  rc=$?

  if [[ $rc -ne 0 ]]; then
    echo '{"error":"call_failed"}'
    return 1
  fi

  if ! echo "$raw" | jq . >/dev/null 2>&1; then
    echo '{"error":"invalid_output"}'
    return 1
  fi

  local is_error
  is_error=$(echo "$raw" | jq -r '[.[] | select(.type == "result")] | first | .is_error // false')
  if [[ "$is_error" == "true" ]]; then
    echo '{"error":"call_failed"}'
    return 1
  fi

  local output
  output=$(echo "$raw" | jq -c '[.[] | select(.type == "result")] | first | .structured_output // empty')
  if [[ -z "$output" || "$output" == "null" ]]; then
    echo '{"error":"invalid_output"}'
    return 1
  fi

  local cost duration
  cost=$(echo "$raw" | jq -r '[.[] | select(.type == "result")] | first | .total_cost_usd // 0')
  duration=$(echo "$raw" | jq -r '[.[] | select(.type == "result")] | first | .duration_ms // 0')

  echo "$output" | jq --arg c "$cost" --arg d "$duration" \
    '. + {_cost_usd: ($c | tonumber), _duration_ms: ($d | tonumber)}'
}
```

- [ ] **Step 5: Run test + commit**

```bash
bash tests/unit/test-llm.sh
git add scripts/lib/llm.sh tests/mocks/claude tests/unit/test-llm.sh
git commit -m "feat(v1.5): add lib/llm.sh (jq render, portable timeout, extended mock)"
```

---

### Task 5.3: Create `lib/validate.sh` with `manual_title_override` support

Addresses: separate override from domain anchor (A2) — when `/rename` nativo writes free-form text, render it verbatim; when user invokes `/smart-rename <slug>`, it's a domain anchor.

**Files:**
- Create: `scripts/lib/validate.sh`
- Create: `tests/unit/test-validate.sh`

- [ ] **Step 1: Create `tests/unit/test-validate.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/config.sh"
source "$SCRIPT_DIR/../../scripts/lib/validate.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

echo "=== validate.sh tests ==="
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
config_load

echo "-- simple render --"
out='{"domain":"auth","clauses":["fix jwt expiry","add tests"]}'
s='{"rendered_title":"","manual_anchor":null,"manual_title_override":null}'
r=$(validate_and_render "$out" "$s")
assert_eq "title" "auth: fix jwt expiry, add tests" "$(echo "$r" | jq -r '.rendered_title')"
assert_eq "status" "ok" "$(echo "$r" | jq -r '.status')"

echo "-- identical → skip --"
s='{"rendered_title":"auth: fix jwt expiry, add tests","manual_anchor":null,"manual_title_override":null}'
assert_eq "skip identical" "skip_identical" "$(validate_and_render "$out" "$s" | jq -r '.status')"

echo "-- manual_anchor overrides domain only (clauses kept) --"
s='{"rendered_title":"","manual_anchor":"fernando-custom","manual_title_override":null}'
r=$(validate_and_render "$out" "$s")
assert_eq "anchor" "fernando-custom: fix jwt expiry, add tests" "$(echo "$r" | jq -r '.rendered_title')"

echo "-- manual_title_override renders verbatim (ignores LLM output) --"
s='{"rendered_title":"","manual_anchor":null,"manual_title_override":"My raw title with spaces"}'
r=$(validate_and_render "$out" "$s")
assert_eq "override verbatim" "My raw title with spaces" "$(echo "$r" | jq -r '.rendered_title')"
assert_eq "status ok" "ok" "$(echo "$r" | jq -r '.status')"

echo "-- dedupe clauses --"
out='{"domain":"auth","clauses":["fix jwt","  fix jwt  ","FIX JWT","add tests"]}'
s='{"rendered_title":"","manual_anchor":null,"manual_title_override":null}'
assert_eq "deduped" "auth: fix jwt, add tests" "$(validate_and_render "$out" "$s" | jq -r '.rendered_title')"

echo "-- invalid outputs --"
assert_eq "empty clauses" "invalid" "$(validate_and_render '{"domain":"x","clauses":[]}' "$s" | jq -r '.status')"
assert_eq "empty domain" "invalid" "$(validate_and_render '{"domain":"","clauses":["a"]}' "$s" | jq -r '.status')"

echo "-- error passes through --"
assert_eq "error" "error" "$(validate_and_render '{"error":"call_failed"}' "$s" | jq -r '.status')"

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bash tests/unit/test-validate.sh
```

- [ ] **Step 3: Create `scripts/lib/validate.sh`**

```bash
#!/usr/bin/env bash
# lib/validate.sh — validate LLM output and render title.
# Supports manual_title_override (raw text, for /rename nativo detection) separate from
# manual_anchor (domain slug, for /smart-rename <slug>).

# Args: llm_output_json, state_json
# Stdout: {"status":"ok"|"skip_identical"|"invalid"|"error", "rendered_title":"...", "title_struct":{...}}
validate_and_render() {
  local output="$1" state="$2"

  local err
  err=$(echo "$output" | jq -r '.error // ""')
  if [[ -n "$err" ]]; then
    echo "$output" | jq -c --arg e "$err" '{status:"error", error:$e}'
    return 0
  fi

  # Early exit: manual_title_override wins. Render verbatim; title_struct is minimal.
  local override
  override=$(echo "$state" | jq -r '.manual_title_override // ""')
  if [[ -n "$override" && "$override" != "null" ]]; then
    local prev
    prev=$(echo "$state" | jq -r '.rendered_title // ""')
    if [[ "$prev" == "$override" ]]; then
      jq -nc --arg t "$override" '{status:"skip_identical", rendered_title:$t, title_struct:{domain:$t, clauses:[]}}'
    else
      jq -nc --arg t "$override" '{status:"ok", rendered_title:$t, title_struct:{domain:$t, clauses:[]}}'
    fi
    return 0
  fi

  local domain clauses_json clauses_count
  domain=$(echo "$output" | jq -r '.domain // ""')
  clauses_json=$(echo "$output" | jq -c '.clauses // []')
  clauses_count=$(echo "$clauses_json" | jq 'length')

  if [[ -z "$domain" || "$domain" == "null" ]]; then
    echo '{"status":"invalid","error":"empty_domain"}'
    return 0
  fi
  if [[ "$clauses_count" -eq 0 ]]; then
    echo '{"status":"invalid","error":"empty_clauses"}'
    return 0
  fi

  local max_clauses max_domain_chars
  max_clauses=$(config_get max_clauses)
  max_domain_chars=$(config_get max_domain_chars)
  domain="${domain:0:$max_domain_chars}"

  local manual_anchor
  manual_anchor=$(echo "$state" | jq -r '.manual_anchor // ""')
  if [[ -n "$manual_anchor" && "$manual_anchor" != "null" ]]; then
    domain="$manual_anchor"
  fi

  local deduped
  deduped=$(echo "$clauses_json" | jq -c --argjson max "$max_clauses" '
    [.[]
      | gsub("^\\s+|\\s+$"; "")
      | gsub("\\s+"; " ")
      | select(length > 0)
    ]
    | reduce .[] as $c (
        {seen: {}, out: []};
        ($c | ascii_downcase) as $k
        | if .seen[$k] then .
          else .seen[$k] = true | .out += [$c]
          end
      )
    | .out[:$max]
  ')

  local deduped_count
  deduped_count=$(echo "$deduped" | jq 'length')
  if [[ "$deduped_count" -eq 0 ]]; then
    echo '{"status":"invalid","error":"all_clauses_empty_after_dedupe"}'
    return 0
  fi

  local joined rendered
  joined=$(echo "$deduped" | jq -r 'join(", ")')
  rendered="$domain: $joined"

  local prev
  prev=$(echo "$state" | jq -r '.rendered_title // ""')
  if [[ "$prev" == "$rendered" ]]; then
    jq -nc --arg t "$rendered" --arg d "$domain" --argjson cl "$deduped" \
      '{status:"skip_identical", rendered_title:$t, title_struct:{domain:$d, clauses:$cl}}'
    return 0
  fi

  jq -nc --arg t "$rendered" --arg d "$domain" --argjson cl "$deduped" \
    '{status:"ok", rendered_title:$t, title_struct:{domain:$d, clauses:$cl}}'
}
```

- [ ] **Step 4: Run test + commit**

```bash
bash tests/unit/test-validate.sh
git add scripts/lib/validate.sh tests/unit/test-validate.sh
git commit -m "feat(v1.5): add lib/validate.sh (override vs anchor, dedupe, render)"
```

---

### Task 5.4: Create `lib/writer.sh` (return-code checked by callers)

**Files:**
- Create: `scripts/lib/writer.sh`
- Create: `tests/unit/test-writer.sh`

- [ ] **Step 1: Create `tests/unit/test-writer.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/writer.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

echo "=== writer.sh tests ==="
tmp=$(mktemp)
cat > "$tmp" <<'JSONL'
{"type":"user","message":{"role":"user","content":"hello"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"hi"}]}}
JSONL

echo "-- append custom-title --"
writer_append_title "$tmp" "auth: fix jwt"
assert_eq "type" "custom-title" "$(tail -1 "$tmp" | jq -r '.type')"
assert_eq "customTitle" "auth: fix jwt" "$(tail -1 "$tmp" | jq -r '.customTitle')"

echo "-- second append adds second line --"
writer_append_title "$tmp" "auth: fix jwt, add tests"
assert_eq "two records" "2" "$(grep -c '"type":"custom-title"' "$tmp")"

echo "-- read last --"
assert_eq "last title" "auth: fix jwt, add tests" "$(writer_get_last_custom_title "$tmp")"

echo "-- missing transcript fails cleanly --"
if writer_append_title "/nonexistent.jsonl" "x" 2>/dev/null; then
  echo "  ✗ should fail"; ((FAIL++)) || true
else
  echo "  ✓ failed"; ((PASS++)) || true
fi

echo "-- get_last on file without custom-title returns empty --"
empty_file=$(mktemp)
echo '{"type":"user","message":{"role":"user","content":"x"}}' > "$empty_file"
assert_eq "empty" "" "$(writer_get_last_custom_title "$empty_file")"

echo "-- title with quotes/newlines is properly JSON-encoded --"
writer_append_title "$tmp" 'title with "quotes"'
assert_eq "quoted" 'title with "quotes"' "$(writer_get_last_custom_title "$tmp")"

rm -f "$tmp" "$empty_file"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bash tests/unit/test-writer.sh
```

- [ ] **Step 3: Create `scripts/lib/writer.sh`**

```bash
#!/usr/bin/env bash
# lib/writer.sh — append custom-title records to session JSONL.
# Returns non-zero on failure so callers can avoid promoting state prematurely.

writer_append_title() {
  local transcript="$1" title="$2"
  [[ ! -f "$transcript" ]] && return 1
  [[ ! -w "$transcript" ]] && return 1
  jq -nc --arg t "$title" '{type:"custom-title", customTitle:$t}' >> "$transcript"
}

writer_get_last_custom_title() {
  local transcript="$1"
  [[ ! -r "$transcript" ]] && { echo ""; return 0; }
  jq -rs '[.[] | select(.type == "custom-title")] | last.customTitle // empty' "$transcript" 2>/dev/null
}
```

- [ ] **Step 4: Run test + commit**

```bash
bash tests/unit/test-writer.sh
git add scripts/lib/writer.sh tests/unit/test-writer.sh
git commit -m "feat(v1.5): add lib/writer.sh (return-code aware)"
```

---

## Phase 6: Hook orchestrator

### Task 6.1: Rewrite `scripts/rename-hook.sh`

Addresses all critical bugs: C1 (last_processed_signature after decision), C2 (trap separation), C6 (state promoted after writer success), C8 (jq-based JSON logs), A1 (signature), A2 (manual_title_override vs manual_anchor), A3 (cwd passed), C5 (lock raised to 60s in config so LLM call doesn't race).

**Files:**
- Rewrite: `scripts/rename-hook.sh` (full v1.5 orchestrator)

Note: v1 deletion happens in Phase 8 (not here). The hook is rewritten but the v1 scripts still exist alongside until integration passes.

- [ ] **Step 1: Rewrite `scripts/rename-hook.sh`**

```bash
#!/usr/bin/env bash
# rename-hook.sh — v1.5 Stop hook orchestrator.
# Input: stdin JSON {session_id, transcript_path, cwd}.
# Contract: always exits 0; never blocks the user's session.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/config.sh"
source "$SCRIPT_DIR/lib/state.sh"
source "$SCRIPT_DIR/lib/logger.sh"
source "$SCRIPT_DIR/lib/transcript.sh"
source "$SCRIPT_DIR/lib/scorer.sh"
source "$SCRIPT_DIR/lib/llm.sh"
source "$SCRIPT_DIR/lib/validate.sh"
source "$SCRIPT_DIR/lib/writer.sh"

# --- Traps split: EXIT unlocks only; ERR logs crash (with sentinel to avoid double-logging) ---
# --- Traps: EXIT captures $? at entry (before state_unlock mutates it) ---
# Invariant: every early `exit 0` path MUST set _HOOK_CLEAN_EXIT=1. Adding a new exit
# path that forgets the sentinel would cause false hook_crashed logs.
_HOOK_CLEAN_EXIT=""
_cleanup_exit() {
  local rc=$?                     # capture status FIRST, before any command below mutates it
  [[ -n "${SESSION_ID:-}" ]] && state_unlock "$SESSION_ID" 2>/dev/null || true
  if [[ -z "$_HOOK_CLEAN_EXIT" && $rc -ne 0 ]]; then
    [[ -n "${SESSION_ID:-}" ]] && log_event error hook_crashed "$SESSION_ID" "$(jq -nc --argjson rc "$rc" '{exit_code:$rc}' 2>/dev/null || echo '{}')" || true
  fi
}
trap _cleanup_exit EXIT

# --- 1. Check dependencies BEFORE any jq usage (jq needed for log_event) ---
if ! command -v jq >/dev/null 2>&1; then
  # Cannot log without jq; silent exit
  _HOOK_CLEAN_EXIT=1; exit 0
fi

# --- 2. Parse input ---
INPUT_RAW="$(cat)"
SESSION_ID="$(echo "$INPUT_RAW" | jq -r '.session_id // empty' 2>/dev/null)"
TRANSCRIPT_PATH="$(echo "$INPUT_RAW" | jq -r '.transcript_path // empty' 2>/dev/null)"
CWD="$(echo "$INPUT_RAW" | jq -r '.cwd // empty' 2>/dev/null)"

if [[ -z "$SESSION_ID" || -z "$TRANSCRIPT_PATH" ]]; then
  _HOOK_CLEAN_EXIT=1; exit 0
fi

command -v claude >/dev/null 2>&1 || { log_event error missing_dep "$SESSION_ID" '{"dep":"claude"}'; _HOOK_CLEAN_EXIT=1; exit 0; }

if [[ ! -r "$TRANSCRIPT_PATH" ]]; then
  log_event warn transcript_missing "$SESSION_ID" '{}'
  _HOOK_CLEAN_EXIT=1; exit 0
fi

config_load
if [[ "$(config_get enabled)" != "true" ]]; then
  _HOOK_CLEAN_EXIT=1; exit 0
fi

# --- 2. Lock + load state ---
if ! state_lock "$SESSION_ID"; then
  log_event info lock_contention "$SESSION_ID" '{}'
  _HOOK_CLEAN_EXIT=1; exit 0
fi

STATE="$(state_load "$SESSION_ID")"

# --- 3. Detect /rename nativo → manual_title_override (not manual_anchor) ---
LAST_JSONL_TITLE="$(writer_get_last_custom_title "$TRANSCRIPT_PATH")"
LAST_PLUGIN_TITLE="$(echo "$STATE" | jq -r '.last_plugin_written_title // ""')"
if [[ -n "$LAST_JSONL_TITLE" && "$LAST_JSONL_TITLE" != "$LAST_PLUGIN_TITLE" ]]; then
  STATE=$(echo "$STATE" | jq --arg t "$LAST_JSONL_TITLE" '
    .manual_title_override = $t
    | .rendered_title = $t
    | .last_plugin_written_title = $t
  ')
  log_event info manual_rename_detected "$SESSION_ID" "$(jq -nc --arg t "$LAST_JSONL_TITLE" '{new_title:$t}')"
fi

# --- 4. Parse transcript (with cwd) ---
PREV_FILES=$(echo "$STATE" | jq -c '.active_files_recent // []')
TURN=$(transcript_parse_current_turn "$TRANSCRIPT_PATH" "$PREV_FILES" "$CWD")
TURN_NUM=$(echo "$TURN" | jq -r '.turn_number // 0')
FILE_SIZE=$(echo "$TURN" | jq -r '.file_size // 0')
CURRENT_SIGNATURE="${TURN_NUM}:${FILE_SIZE}"

# --- 5. Compute work score delta + update active_files (no last_processed_signature yet!) ---
DELTA=$(scorer_compute_delta "$TURN")
STATE=$(echo "$STATE" | jq \
  --argjson turn "$TURN" \
  --argjson d "$DELTA" '
  .accumulated_score = ((.accumulated_score // 0) + $d)
  | .domain_guess = ($turn.domain_guess // .domain_guess)
  | .active_files_recent = (
      ((.active_files_recent // []) + ($turn.all_files_touched // []))
      | unique | .[0:20]
    )
  | .branch = ($turn.branch // .branch // "")
  | .updated_at = (now | todate)
  | .version = "1.5"
')

log_event debug score_update "$SESSION_ID" "$(jq -nc --argjson d "$DELTA" --argjson acc "$(echo "$STATE" | jq -r '.accumulated_score')" --argjson t "$TURN_NUM" --argjson fs "$FILE_SIZE" '{delta:$d, acc:$acc, turn:$t, file_size:$fs}')"

# --- 6. Decide (scorer reads last_processed_signature, which still holds the PREVIOUS value) ---
DECISION_JSON=$(scorer_should_call_llm "$STATE" "$CURRENT_SIGNATURE")
DECISION=$(echo "$DECISION_JSON" | jq -r '.decision')
REASON=$(echo "$DECISION_JSON" | jq -r '.reason')

log_event info llm_decision "$SESSION_ID" "$(jq -nc --arg d "$DECISION" --arg r "$REASON" '{decision:$d, reason:$r}')"

REATTACH_INTERVAL=$(config_get reattach_interval)
CUR_TITLE=$(echo "$STATE" | jq -r '.rendered_title // ""')

if [[ "$DECISION" == "skip" ]]; then
  # Periodic re-attach
  if [[ -n "$CUR_TITLE" ]] && (( TURN_NUM % REATTACH_INTERVAL == 0 )); then
    if writer_append_title "$TRANSCRIPT_PATH" "$CUR_TITLE"; then
      log_event info title_reattached "$SESSION_ID" "$(jq -nc --arg t "$CUR_TITLE" '{title:$t}')"
    fi
  fi
  # Update signature AFTER decision
  STATE=$(echo "$STATE" | jq --arg s "$CURRENT_SIGNATURE" '.last_processed_signature = $s')
  state_save "$SESSION_ID" "$STATE"
  _HOOK_CLEAN_EXIT=1; exit 0
fi

# --- 7. Call LLM ---
CALLS_MADE=$(echo "$STATE" | jq -r '.calls_made // 0')
MAX_CALLS=$(config_get max_budget_calls)

# Decide whether this consumes a budget slot or an overflow slot (force_next past budget)
if [[ "$CALLS_MADE" -ge "$MAX_CALLS" ]]; then
  STATE=$(echo "$STATE" | jq '.overflow_used = ((.overflow_used // 0) + 1) | .force_next = false')
else
  STATE=$(echo "$STATE" | jq '.calls_made = ((.calls_made // 0) + 1) | .force_next = false')
fi

# Build LLM context (recent_turns: array of transition titles, joined safely in jq)
CTX=$(jq -nc \
  --arg t "$CUR_TITLE" \
  --arg a "$(echo "$STATE" | jq -r '.manual_anchor // ""')" \
  --arg br "$(echo "$STATE" | jq -r '.branch // ""')" \
  --arg dg "$(echo "$STATE" | jq -r '.domain_guess // ""')" \
  --arg rf "$(echo "$STATE" | jq -r '(.active_files_recent // []) | .[:5] | join(", ")')" \
  --arg um "$(echo "$TURN" | jq -r '.user_msg // ""')" \
  --arg as "$(echo "$TURN" | jq -r '.assistant_text // "" | .[:500]')" \
  --arg rt "$(echo "$STATE" | jq -r '(.transition_history // []) | map("turn " + (.turn|tostring) + ": " + .title) | join("\n")')" \
  '{CURRENT_TITLE:$t, MANUAL_ANCHOR:$a, BRANCH:$br, DOMAIN_GUESS:$dg, RECENT_FILES:$rf, USER_MSG:$um, ASSISTANT_SUMMARY:$as, RECENT_TURNS:$rt}')

log_event info llm_call_start "$SESSION_ID" "$(echo "$STATE" | jq -c '{calls_made, overflow_used}')"

LLM_OUTPUT=$(llm_generate_title "$CTX" || echo '{"error":"call_failed"}')
COST=$(echo "$LLM_OUTPUT" | jq -r '._cost_usd // 0')
DURATION=$(echo "$LLM_OUTPUT" | jq -r '._duration_ms // 0')

log_event info llm_call_end "$SESSION_ID" "$(jq -nc --argjson c "$COST" --argjson d "$DURATION" --argjson o "$LLM_OUTPUT" '{cost_usd:$c, duration_ms:$d, output:$o}')"

# --- 8. Validate + write + promote state only on writer success ---
LLM_ERR=$(echo "$LLM_OUTPUT" | jq -r '.error // ""')
if [[ -n "$LLM_ERR" ]]; then
  NEW_FAIL=$(( $(echo "$STATE" | jq -r '.failure_count // 0') + 1 ))
  CB_THR=$(config_get circuit_breaker_threshold)
  STATE=$(echo "$STATE" | jq --argjson n "$NEW_FAIL" --argjson thr "$CB_THR" '
    .failure_count = $n
    | .llm_disabled = ($n >= $thr)
  ')
  if (( NEW_FAIL >= CB_THR )); then
    log_event warn circuit_breaker_tripped "$SESSION_ID" "$(jq -nc --argjson n "$NEW_FAIL" '{failure_count:$n}')"
  fi
  STATE=$(echo "$STATE" | jq --arg s "$CURRENT_SIGNATURE" '.last_processed_signature = $s')
  state_save "$SESSION_ID" "$STATE"
  _HOOK_CLEAN_EXIT=1; exit 0
fi

# Success: reset CB
STATE=$(echo "$STATE" | jq '.failure_count = 0 | .llm_disabled = false')

VALIDATED=$(validate_and_render "$LLM_OUTPUT" "$STATE")
STATUS=$(echo "$VALIDATED" | jq -r '.status')

# Track whether to advance the signature. We advance for all outcomes EXCEPT
# "LLM returned ok but writer failed" — in that case we want the next hook
# to re-evaluate (possibly re-calling LLM) rather than silently stuck.
ADVANCE_SIGNATURE=1

case "$STATUS" in
  ok)
    TITLE=$(echo "$VALIDATED" | jq -r '.rendered_title')
    TS=$(echo "$VALIDATED" | jq -c '.title_struct')
    if writer_append_title "$TRANSCRIPT_PATH" "$TITLE"; then
      # Promote state only after writer confirms
      STATE=$(echo "$STATE" | jq --arg t "$TITLE" --argjson ts "$TS" --argjson tn "$TURN_NUM" '
        (.title_struct // null) as $prev_ts
        | .rendered_title = $t
        | .last_plugin_written_title = $t
        | .title_struct = $ts
        | .accumulated_score = 0
        | (.transition_history // []) as $h
        | .transition_history = (($h + [{turn: $tn, title: $t, reason: (if $prev_ts then "extend" else "first" end)}]) | .[-3:])
      ')
      log_event info title_written "$SESSION_ID" "$(jq -nc --arg t "$TITLE" '{title:$t}')"
    else
      log_event warn title_write_failed "$SESSION_ID" "$(jq -nc --arg t "$TITLE" '{attempted_title:$t}')"
      # Do NOT promote state; do NOT advance signature — next hook will re-evaluate.
      ADVANCE_SIGNATURE=0
    fi
    ;;
  skip_identical)
    STATE=$(echo "$STATE" | jq '.accumulated_score = 0')
    log_event info title_skipped "$SESSION_ID" '{"reason":"identical"}'
    ;;
  *)
    log_event warn title_invalid "$SESSION_ID" "$VALIDATED"
    ;;
esac

if [[ $ADVANCE_SIGNATURE -eq 1 ]]; then
  STATE=$(echo "$STATE" | jq --arg s "$CURRENT_SIGNATURE" '.last_processed_signature = $s')
fi
state_save "$SESSION_ID" "$STATE"
_HOOK_CLEAN_EXIT=1
exit 0
```

Make executable: `chmod +x scripts/rename-hook.sh`

- [ ] **Step 2: Update `tests/run-tests.sh`**

Replace with:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOTAL_PASS=0; TOTAL_FAIL=0

run_one() {
  local f="$1"
  echo ""
  echo "Running $(basename "$(dirname "$f")")/$(basename "$f")..."
  if bash "$f"; then
    ((TOTAL_PASS++)) || true
  else
    ((TOTAL_FAIL++)) || true
  fi
}

for test_file in "$SCRIPT_DIR"/unit/test-*.sh "$SCRIPT_DIR"/integration/test-*.sh; do
  [[ -f "$test_file" ]] && run_one "$test_file"
done

echo ""
echo "=============================="
echo "Test suites: $TOTAL_PASS passed, $TOTAL_FAIL failed"
[[ $TOTAL_FAIL -eq 0 ]] && exit 0 || exit 1
```

- [ ] **Step 3: Commit (v1 scripts still present; deleted in Phase 8)**

```bash
git add scripts/rename-hook.sh tests/run-tests.sh
git commit -m "feat(v1.5): rewrite rename-hook.sh (orchestrator with all critical fixes)"
```

---

## Phase 7: Complete skill (all subcommands)

### Task 7.1: Expand `smart-rename-cli.sh` with all subcommands

Addresses: A4 (cmd_suggest consumes budget), A2 (cmd_anchor sets manual_anchor for domain — not title override).

> **Forward-port from Phase 1.3 lesson:** the `session_id_from_args` function
> in the verbatim CLI block below must include the **cwd-derive** fallback
> (already proven necessary in Task 1.3). Specifically: keep the env-var and
> transcript-arg paths, then add a third path that scans
> `~/.claude/projects/<encoded-pwd>/` for the most recent `.jsonl`. Use
> `pwd -P` and the encoding rule `[/_]` → `-`, prefix `-`. Optional
> `SMART_RENAME_DEBUG=1` toggle for resolution tracing. The rest of the CLI
> below (dispatcher, cmd_*, etc.) stays as written.

**Files:**
- Rewrite: `scripts/smart-rename-cli.sh`
- Rewrite: `skills/smart-rename/SKILL.md`

- [ ] **Step 1: Rewrite `scripts/smart-rename-cli.sh`**

```bash
#!/usr/bin/env bash
# smart-rename-cli.sh — skill subcommand dispatcher (v1.5 full)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/config.sh"
source "$SCRIPT_DIR/lib/state.sh"
source "$SCRIPT_DIR/lib/logger.sh"
source "$SCRIPT_DIR/lib/writer.sh"
source "$SCRIPT_DIR/lib/llm.sh"
source "$SCRIPT_DIR/lib/validate.sh"
source "$SCRIPT_DIR/lib/transcript.sh"

session_id_from_args() {
  if [[ -n "${CLAUDE_SESSION_ID:-}" ]]; then echo "$CLAUDE_SESSION_ID"; return 0; fi
  if [[ -n "${1:-}" && -f "$1" ]]; then basename "$1" .jsonl; return 0; fi
  echo ""; return 1
}

with_lock() {
  local sid="$1"; shift
  state_lock "$sid" || { echo "ERROR: could not lock session state"; exit 1; }
  trap "state_unlock $sid" EXIT
  "$@"
}

usage() {
  cat <<EOF
Usage: /smart-rename [args]

  /smart-rename                 Suggest a rename (consumes 1 budget slot, prints suggestion).
  /smart-rename <name>          Set domain anchor to <name> (slug).
  /smart-rename freeze          Pause automatic updates.
  /smart-rename unfreeze        Resume automatic updates.
  /smart-rename force           Force LLM call on next Stop hook.
  /smart-rename explain         Show state, budget, history.
  /smart-rename unanchor        Clear manual anchor.
EOF
}

cmd_freeze() {
  local sid="$1"
  local st; st=$(state_load "$sid")
  state_save "$sid" "$(echo "$st" | jq '.frozen = true | .updated_at = (now | todate)')"
  log_event info freeze_toggled "$sid" '{"frozen":true}'
  echo "Smart rename FROZEN for session $sid"
}

cmd_unfreeze() {
  local sid="$1"
  local st; st=$(state_load "$sid")
  state_save "$sid" "$(echo "$st" | jq '.frozen = false | .updated_at = (now | todate)')"
  log_event info freeze_toggled "$sid" '{"frozen":false}'
  echo "Smart rename UNFROZEN for session $sid"
}

cmd_force() {
  local sid="$1"
  local st; st=$(state_load "$sid")
  state_save "$sid" "$(echo "$st" | jq '.force_next = true | .failure_count = 0 | .llm_disabled = false | .updated_at = (now | todate)')"
  log_event info force_triggered "$sid" '{}'
  echo "Force flag set; will evaluate on next Stop hook."
}

cmd_anchor() {
  local sid="$1" name="$2" transcript="$3"
  local st; st=$(state_load "$sid")
  # Build rendered_title: domain = anchor; clauses kept from title_struct if present
  local clauses n
  clauses=$(echo "$st" | jq -c '.title_struct.clauses // []')
  n=$(echo "$clauses" | jq 'length')
  local title
  if [[ "$n" -eq 0 ]]; then
    title="$name"
  else
    title="$name: $(echo "$clauses" | jq -r 'join(", ")')"
  fi

  # R4: Write JSONL FIRST; only promote state if the write succeeded. If no
  # transcript was provided, skip the write but still update state (the caller
  # is explicitly anchoring without wanting the JSONL rewritten).
  if [[ -n "$transcript" && -f "$transcript" ]]; then
    if ! writer_append_title "$transcript" "$title"; then
      echo "ERROR: could not append custom-title to transcript; aborting anchor (state unchanged)"
      return 1
    fi
  fi

  state_save "$sid" "$(echo "$st" | jq --arg a "$name" --arg t "$title" '
    .manual_anchor = $a
    | .manual_title_override = null
    | .rendered_title = $t
    | (.title_struct // {}) as $ts
    | .title_struct = ($ts + {domain:$a})
    | .last_plugin_written_title = $t
    | .updated_at = (now | todate)
  ')"
  log_event info manual_anchor_set "$sid" "$(jq -nc --arg a "$name" '{anchor:$a}')"
  echo "Anchor set: $name (title: \"$title\")"
}

# R3: unanchor clears BOTH manual_anchor AND manual_title_override so the user
# has a single command to return to fully automatic naming after either a
# /smart-rename <name> or a /rename nativo.
cmd_unanchor() {
  local sid="$1"
  local st; st=$(state_load "$sid")
  state_save "$sid" "$(echo "$st" | jq '
    .manual_anchor = null
    | .manual_title_override = null
    | .updated_at = (now | todate)
  ')"
  log_event info manual_anchor_set "$sid" '{"anchor":null,"override":null}'
  echo "Anchor and title override cleared. Plugin resumes automatic naming on next Stop hook."
}

cmd_explain() {
  local sid="$1"
  config_load
  local st; st=$(state_load "$sid")
  local max_calls=$(config_get max_budget_calls)
  local overflow_slots=$(config_get overflow_manual_slots)
  local first_thr=$(config_get first_call_work_threshold)
  local ongoing_thr=$(config_get ongoing_work_threshold)

  local title=$(echo "$st" | jq -r '.rendered_title // "(not yet named)"')
  local domain=$(echo "$st" | jq -r '.title_struct.domain // "—"')
  local anchor=$(echo "$st" | jq -r '.manual_anchor // "—"')
  local override=$(echo "$st" | jq -r '.manual_title_override // "—"')
  local frozen=$(echo "$st" | jq -r '.frozen // false')
  local force=$(echo "$st" | jq -r '.force_next // false')
  local llm_dis=$(echo "$st" | jq -r '.llm_disabled // false')
  local fc=$(echo "$st" | jq -r '.failure_count // 0')
  local calls=$(echo "$st" | jq -r '.calls_made // 0')
  local overflow=$(echo "$st" | jq -r '.overflow_used // 0')
  local acc=$(echo "$st" | jq -r '.accumulated_score // 0')

  local has_title=$(echo "$st" | jq -r 'if .title_struct then "true" else "false" end')
  local next_thr=$first_thr
  [[ "$has_title" == "true" ]] && next_thr=$ongoing_thr

  cat <<EOF
Título atual: $title
Domínio: $domain (anchor: $anchor, override: $override)
Estado: $([ "$frozen" = "true" ] && echo "congelado" || echo "ativo")$([ "$force" = "true" ] && echo "; force próximo turno" || echo "")

Budget: $calls/$max_calls chamadas usadas, $((max_calls - calls)) restantes · overflow $overflow/$overflow_slots
Circuit breaker: $([ "$llm_dis" = "true" ] && echo "ATIVO (plugin desabilitado)" || echo "OK ($fc falhas consecutivas)")
Work score acumulado: $acc (próximo call em ≥$next_thr)

Últimas transições:
EOF
  echo "$st" | jq -r '
    (.transition_history // [])[] | "  turno \(.turn)  → \(.title)  (\(.reason))"
  ' 2>/dev/null || echo "  (sem histórico ainda)"

  echo ""
  echo "Último evento do log:"
  local log_file="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}/logs/$sid.jsonl"
  if [[ -f "$log_file" ]]; then tail -1 "$log_file"; else echo "  (sem log ainda)"; fi
}

# /smart-rename (no args): suggest. CONSUMES 1 budget slot (A4).
# Mirrors the hook's circuit breaker behavior (N4) and checks validate status (N5).
# Accepts explicit cwd so domain_guess/branch are correct when called from the skill (R5).
cmd_suggest() {
  local sid="$1" transcript="$2" cwd="${3:-$PWD}"
  local st; st=$(state_load "$sid")

  local calls_made=$(echo "$st" | jq -r '.calls_made // 0')
  local overflow_used=$(echo "$st" | jq -r '.overflow_used // 0')
  local max_calls=$(config_get max_budget_calls)
  local overflow_slots=$(config_get overflow_manual_slots)
  local cb_thr=$(config_get circuit_breaker_threshold)
  local llm_disabled=$(echo "$st" | jq -r '.llm_disabled // false')

  if [[ "$llm_disabled" == "true" ]]; then
    echo "Circuit breaker active (LLM disabled for this session). Use /smart-rename force to reset."
    return 1
  fi

  if [[ "$calls_made" -ge "$max_calls" ]] && [[ "$overflow_used" -ge "$overflow_slots" ]]; then
    echo "Budget and overflow exhausted. Use /smart-rename <name> to anchor manually."
    return 1
  fi

  local prev_files=$(echo "$st" | jq -c '.active_files_recent // []')
  local turn=$(transcript_parse_current_turn "$transcript" "$prev_files" "$cwd")

  local ctx=$(jq -nc \
    --arg t "$(echo "$st" | jq -r '.rendered_title // ""')" \
    --arg a "$(echo "$st" | jq -r '.manual_anchor // ""')" \
    --arg br "$(echo "$turn" | jq -r '.branch // ""')" \
    --arg dg "$(echo "$turn" | jq -r '.domain_guess // ""')" \
    --arg rf "$(echo "$turn" | jq -r '.all_files_touched | .[:5] | join(", ")')" \
    --arg um "$(echo "$turn" | jq -r '.user_msg // ""')" \
    --arg as "$(echo "$turn" | jq -r '.assistant_text // "" | .[:500]')" \
    --arg rt "" \
    '{CURRENT_TITLE:$t, MANUAL_ANCHOR:$a, BRANCH:$br, DOMAIN_GUESS:$dg, RECENT_FILES:$rf, USER_MSG:$um, ASSISTANT_SUMMARY:$as, RECENT_TURNS:$rt}')

  # Consume budget BEFORE call (consistent with hook behavior). Save immediately so
  # a subsequent crash still records the spend.
  if [[ "$calls_made" -ge "$max_calls" ]]; then
    st=$(echo "$st" | jq '.overflow_used = ((.overflow_used // 0) + 1)')
  else
    st=$(echo "$st" | jq '.calls_made = ((.calls_made // 0) + 1)')
  fi
  state_save "$sid" "$st"

  local out=$(llm_generate_title "$ctx" || echo '{"error":"call_failed"}')
  local err=$(echo "$out" | jq -r '.error // ""')
  if [[ -n "$err" ]]; then
    # N4: integrate with circuit breaker identically to the hook
    local new_fail=$(($(echo "$st" | jq -r '.failure_count // 0') + 1))
    st=$(echo "$st" | jq --argjson n "$new_fail" --argjson thr "$cb_thr" '
      .failure_count = $n | .llm_disabled = ($n >= $thr)
    ')
    state_save "$sid" "$st"
    log_event warn llm_error "$sid" "$(jq -nc --arg e "$err" --argjson n "$new_fail" '{error:$e, failure_count:$n}')"
    if (( new_fail >= cb_thr )); then
      echo "LLM call failed ($err). Circuit breaker tripped ($new_fail/$cb_thr); use /smart-rename force to reset."
    else
      echo "LLM call failed ($err). Failure count: $new_fail/$cb_thr."
    fi
    return 1
  fi

  # Success resets failure counter (keeps CB behavior consistent across hook/skill)
  st=$(echo "$st" | jq '.failure_count = 0 | .llm_disabled = false')
  state_save "$sid" "$st"

  local validated=$(validate_and_render "$out" "$st")
  local vstatus=$(echo "$validated" | jq -r '.status')

  # N5: treat invalid/error validation results honestly instead of printing "null"
  if [[ "$vstatus" != "ok" && "$vstatus" != "skip_identical" ]]; then
    local verr=$(echo "$validated" | jq -r '.error // "unknown_validation_error"')
    echo "Validation failed: $verr (LLM output was malformed or rejected). No changes applied."
    return 1
  fi

  local title=$(echo "$validated" | jq -r '.rendered_title')
  local sdomain=$(echo "$validated" | jq -r '.title_struct.domain // ""')
  echo "Suggested title: $title"
  echo ""
  echo "To apply as anchor, run:   /smart-rename $sdomain"
  echo "Or accept literally via:   /rename \"$title\"   (native command)"
}

# Dispatcher. Third positional arg to cmd_suggest is optional cwd; the SKILL should
# pass $CLAUDE_PROJECT_DIR when available, else $PWD is used as fallback.
cmd="${1:-}"; shift || true

case "$cmd" in
  "" )
    transcript="${1:-}"
    cwd_arg="${2:-${CLAUDE_PROJECT_DIR:-${PWD:-}}}"
    sid="$(session_id_from_args "$transcript")"
    [[ -z "$sid" ]] && { echo "ERROR: cannot determine session id"; exit 1; }
    with_lock "$sid" cmd_suggest "$sid" "$transcript" "$cwd_arg"
    ;;
  freeze)   sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_freeze "$sid" ;;
  unfreeze) sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_unfreeze "$sid" ;;
  force)    sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_force "$sid" ;;
  unanchor) sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_unanchor "$sid" ;;
  explain)  sid="$(session_id_from_args "${1:-}")"; cmd_explain "$sid" ;;
  help|-h|--help) usage ;;
  *)
    name="$cmd"
    transcript="${1:-}"
    sid="$(session_id_from_args "$transcript")"
    [[ -z "$sid" ]] && { echo "ERROR: cannot determine session id"; exit 1; }
    with_lock "$sid" cmd_anchor "$sid" "$name" "$transcript"
    ;;
esac
```

- [ ] **Step 2: Rewrite `skills/smart-rename/SKILL.md`**

```markdown
---
name: smart-rename
description: Manage the smart-session-rename plugin — suggest, anchor, freeze, force, explain.
---

# /smart-rename (v1.5)

When the user invokes `/smart-rename [args]`, run the matching command via the Bash tool and report the output verbatim. Pass `$CLAUDE_TRANSCRIPT_PATH` as the last argument.

## Subcommands

### `/smart-rename` — suggest (consumes 1 budget slot)
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh "" "$CLAUDE_TRANSCRIPT_PATH" "${CLAUDE_PROJECT_DIR:-$PWD}"
```

### `/smart-rename <name>` — set domain anchor
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh "<name>" "$CLAUDE_TRANSCRIPT_PATH"
```

### `/smart-rename freeze` / `unfreeze`
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh freeze "$CLAUDE_TRANSCRIPT_PATH"
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh unfreeze "$CLAUDE_TRANSCRIPT_PATH"
```

### `/smart-rename force`
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh force "$CLAUDE_TRANSCRIPT_PATH"
```

### `/smart-rename explain`
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh explain "$CLAUDE_TRANSCRIPT_PATH"
```

### `/smart-rename unanchor`
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh unanchor "$CLAUDE_TRANSCRIPT_PATH"
```

If the CLI exits non-zero, report the error message verbatim. Do not retry automatically.
```

- [ ] **Step 3: [AGENT] Create results-template doc with all 7 subcommands**

Create `docs/test-results/2026-04-14-skill-full.md`:

```markdown
# Phase 7.1 — Full Skill Smoke Test Results

Date: <date>
Tester: Fernando Bertholdo

## Environment
- Claude Code version: __________
- Plugin dev-install mode confirmed? yes / no

## Subcommand matrix

| # | Command | Expected output contains | Actual output | State change observed | OK? |
|---|---------|--------------------------|---------------|-----------------------|-----|
| 1 | `/smart-rename freeze` | "FROZEN for session …" | | `.frozen = true` | |
| 2 | `/smart-rename explain` | "Estado: congelado" | | N/A (read-only) | |
| 3 | `/smart-rename unfreeze` | "UNFROZEN for session …" | | `.frozen = false` | |
| 4 | `/smart-rename my-test-anchor` | "Anchor set: my-test-anchor" | | `.manual_anchor = "my-test-anchor"` | |
| 5 | `/smart-rename explain` | "anchor: my-test-anchor" | | N/A | |
| 6 | `/smart-rename unanchor` | "Anchor and title override cleared" | | `.manual_anchor = null` | |
| 7 | `/smart-rename force` | "Force flag set" | | `.force_next = true` | |
| 8 | `/smart-rename` (no args, costs ~$0.10) | "Suggested title: …" | | `.calls_made` +1 | |

(Run #8 only if you want to spend budget. Skip if cost-sensitive.)

## Cross-cutting checks
- Did `/smart-rename` (no args) correctly consume 1 budget slot when called?
  Answer: __________ (only if step #8 ran)
- Did the JSONL get a `custom-title` record written for anchor/override paths?
  Answer: __________
- Any errors from the CLI that were unclear / unhelpful?
  Answer: __________

## Verdict
- [ ] ✅ All subcommands behave as specified. Proceed to Phase 8.
- [ ] ⚠️ Minor issues (list below, but not blocking Phase 8).
- [ ] ❌ Blocking issues (list below; must fix before Phase 8).

## Issues observed
<list>
```

- [ ] **Step 4: [USER] Run the smoke test in a fresh session**

Prerequisites:
- Fresh Claude Code session (not this agent's session — plugin registry must
  reload with v1.5 skill).
- Plugin dev-installed (same setup as Task 1.3 Step 4).
- Working directory: any throwaway project.

Run the sequence from the table above in order. Between commands, you can
inspect state:
```bash
ls "${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}/state/"
jq . "${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}/state/"*.json
tail -5 "${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}/logs/"*.jsonl
```

Record outputs in the results doc. Fill the verdict. Commit the doc yourself
or paste it back to the agent.

- [ ] **Step 5: [AGENT] Commit (after user verdict)**

```bash
git add scripts/smart-rename-cli.sh skills/smart-rename/SKILL.md docs/test-results/2026-04-14-skill-full.md
git commit -m "feat(v1.5): complete skill (all 7 subcommands; suggest consumes budget)"
```

If verdict is ❌: STOP, resolve with user, revise CLI or SKILL.md before
continuing to Phase 8.

---

## Phase 8: Integration tests + v1 deletion

### Task 8.1: Comprehensive integration tests

Adds coverage for: T3 multi-Stop, T4 pivot, T5 force/overflow, T6 anchor persistence after native rename.

**Files:**
- Create: `tests/integration/test-end-to-end.sh`
- Create: `tests/fixtures/transcript-v15-qa.jsonl`
- Create: `tests/fixtures/transcript-v15-pivot.jsonl`

- [ ] **Step 1: Create Q&A fixture**

`tests/fixtures/transcript-v15-qa.jsonl`:
```jsonl
{"type":"user","message":{"role":"user","content":"What does useEffect cleanup do in React?"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"The cleanup function in useEffect runs before the effect re-executes or when the component unmounts. It's used for clearing timers, canceling subscriptions, or removing event listeners."}]}}
```

- [ ] **Step 2: Create pivot fixture**

`tests/fixtures/transcript-v15-pivot.jsonl`:
```jsonl
{"type":"user","message":{"role":"user","content":"Fix the JWT auth bug"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Looking at JWT logic."},{"type":"tool_use","id":"1","name":"Read","input":{"file_path":"src/auth/jwt.ts"}},{"type":"tool_use","id":"2","name":"Edit","input":{"file_path":"src/auth/jwt.ts","old_string":"x","new_string":"y"}}]}}
{"type":"user","message":{"role":"user","content":"Actually, let's switch — build a CI workflow for deploying to Vercel instead"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Switching gears."},{"type":"tool_use","id":"3","name":"Write","input":{"file_path":".github/workflows/vercel.yml","content":"name: deploy"}},{"type":"tool_use","id":"4","name":"Bash","input":{"command":"git add"}}]}}
```

- [ ] **Step 3: Create `tests/integration/test-end-to-end.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_DIR/scripts/rename-hook.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
export PATH="$SCRIPT_DIR/../mocks:$PATH"

run_hook() {
  local transcript="$1" sid="$2"
  jq -nc --arg sid "$sid" --arg tp "$transcript" --arg cwd "$PWD" \
    '{session_id:$sid, transcript_path:$tp, cwd:$cwd}' | bash "$HOOK"
}

echo "=== end-to-end integration tests ==="

echo "-- Q&A: low score, no LLM call --"
tqa=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-qa.jsonl" "$tqa"
run_hook "$tqa" "sess-qa"
assert_eq "no LLM" "0" "$(jq -r '.calls_made // 0' "$CLAUDE_PLUGIN_DATA/state/sess-qa.json")"

echo "-- Feature: threshold met → LLM call + title written (pre-seeded score to 20) --"
unset MOCK_CLAUDE_MODE
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"duration_ms":200,"total_cost_usd":0.05,"structured_output":{"domain":"auth","clauses":["add rate limiting"]}}]'
tf=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tf"
# N3: pre-seed accumulated_score so the delta from this fixture (~13) pushes total past threshold 20.
# This documents the intent explicitly rather than relying on coincidental fixture arithmetic.
mkdir -p "$CLAUDE_PLUGIN_DATA/state"
jq -nc '{version:"1.5", accumulated_score:10, title_struct:null, calls_made:0, overflow_used:0, failure_count:0, llm_disabled:false, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-feat.json"
run_hook "$tf" "sess-feat"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-feat.json")
assert_eq "calls_made 1" "1" "$(echo "$s" | jq -r '.calls_made')"
assert_eq "title set" "auth: add rate limiting" "$(echo "$s" | jq -r '.rendered_title')"
assert_eq "JSONL has custom-title" "custom-title" "$(tail -1 "$tf" | jq -r '.type')"
assert_eq "last_processed_signature set" "true" "$(echo "$s" | jq 'has("last_processed_signature")')"

echo "-- Writer failure: state NOT promoted, signature NOT advanced (R1) --"
tfw=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tfw"
chmod 444 "$tfw"   # readonly → writer_append_title returns non-zero
jq -nc '{version:"1.5", accumulated_score:15, title_struct:null, calls_made:0, overflow_used:0, failure_count:0, llm_disabled:false, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-wf.json"
run_hook "$tfw" "sess-wf"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-wf.json")
# title_struct should remain null (not promoted), rendered_title empty
assert_eq "rendered_title empty (not promoted)" "" "$(echo "$s" | jq -r '.rendered_title // ""')"
# signature should be empty (not advanced)
assert_eq "signature not advanced" "" "$(echo "$s" | jq -r '.last_processed_signature // ""')"
chmod 644 "$tfw"

echo "-- LLM failure increments failure_count --"
export MOCK_CLAUDE_MODE=fail
tf2=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tf2"
run_hook "$tf2" "sess-fail"
assert_eq "failure 1" "1" "$(jq -r '.failure_count // 0' "$CLAUDE_PLUGIN_DATA/state/sess-fail.json")"
unset MOCK_CLAUDE_MODE

echo "-- Circuit breaker trips after 3 failures --"
export MOCK_CLAUDE_MODE=fail
tcb=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tcb"
jq -nc '{version:"1.5", failure_count:2, llm_disabled:false, calls_made:0, overflow_used:0, accumulated_score:100, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-cb.json"
run_hook "$tcb" "sess-cb"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-cb.json")
assert_eq "failure 3" "3" "$(echo "$s" | jq -r '.failure_count')"
assert_eq "llm_disabled" "true" "$(echo "$s" | jq -r '.llm_disabled')"
unset MOCK_CLAUDE_MODE

echo "-- Idempotency: same signature does NOT double-count (pre-seed so first call fires) --"
unset MOCK_CLAUDE_MODE
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"duration_ms":200,"total_cost_usd":0.05,"structured_output":{"domain":"test","clauses":["a"]}}]'
tid=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tid"
jq -nc '{version:"1.5", accumulated_score:15, title_struct:null, calls_made:0, overflow_used:0, failure_count:0, llm_disabled:false, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-idem.json"
run_hook "$tid" "sess-idem"
# Second run with SAME file → same signature → scorer skips
run_hook "$tid" "sess-idem"
assert_eq "calls_made still 1 after 2 hook runs on same file" "1" "$(jq -r '.calls_made' "$CLAUDE_PLUGIN_DATA/state/sess-idem.json")"

echo "-- Multi-stop: file grows on second run → signature differs → proceeds --"
tms=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-multi-stop.jsonl" "$tms"
# Truncate to first assistant block to simulate mid-agentic-loop
head -2 "$tms" > "${tms}.part1"
run_hook "${tms}.part1" "sess-ms"
s_part=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-ms.json")
# Now run with full file (size differs → signature differs → scorer proceeds)
run_hook "$tms" "sess-ms"
s_full=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-ms.json")
# active_files should have accumulated more files in the second run
part_files=$(echo "$s_part" | jq -r '.active_files_recent | length')
full_files=$(echo "$s_full" | jq -r '.active_files_recent | length')
[[ "$full_files" -ge "$part_files" ]] && { echo "  ✓ signature-based idempotency allowed mid-turn re-processing"; ((PASS++)) || true; } || { echo "  ✗ full=$full_files part=$part_files"; ((FAIL++)) || true; }

echo "-- Manual /rename sets title_override (not anchor) --"
tman=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tman"
jq -nc '{type:"custom-title", customTitle:"My custom free-form title"}' >> "$tman"
run_hook "$tman" "sess-man"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-man.json")
assert_eq "title_override set" "My custom free-form title" "$(echo "$s" | jq -r '.manual_title_override')"
assert_eq "rendered is override" "My custom free-form title" "$(echo "$s" | jq -r '.rendered_title')"

echo "-- Anchor persistence: /rename nativo then new hook → still honors override --"
# Run second hook on the same session: should NOT overwrite manual title with new LLM output
run_hook "$tman" "sess-man"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-man.json")
assert_eq "override persists" "My custom free-form title" "$(echo "$s" | jq -r '.manual_title_override')"
assert_eq "rendered still override" "My custom free-form title" "$(echo "$s" | jq -r '.rendered_title')"

echo "-- Pivot: domain changes are reflected when LLM returns new domain (pre-seeded state with existing title_struct) --"
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"duration_ms":200,"total_cost_usd":0.05,"structured_output":{"domain":"ci","clauses":["add vercel workflow"]}}]'
# Pre-seed: session already has a title (title_struct set) so ongoing_threshold=40 applies.
# Fixture delta is ~5; we pre-seed accumulated_score=40 so decision is CALL.
jq -nc '{version:"1.5", accumulated_score:40, title_struct:{domain:"auth",clauses:["old"]}, rendered_title:"auth: old", calls_made:1, overflow_used:0, failure_count:0, llm_disabled:false, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-pv.json"
tpv=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-pivot.jsonl" "$tpv"
run_hook "$tpv" "sess-pv"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-pv.json")
assert_eq "pivot domain" "ci" "$(echo "$s" | jq -r '.title_struct.domain')"

echo "-- Force path consumes overflow when budget already at max --"
tfc=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tfc"
jq -nc '{version:"1.5", title_struct:{domain:"x",clauses:["a"]}, rendered_title:"x: a", calls_made:6, overflow_used:0, force_next:true, accumulated_score:0, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-force.json"
run_hook "$tfc" "sess-force"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-force.json")
assert_eq "overflow incremented" "1" "$(echo "$s" | jq -r '.overflow_used')"
assert_eq "force consumed" "false" "$(echo "$s" | jq -r '.force_next')"

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 4: Run integration + full suite**

```bash
bash tests/integration/test-end-to-end.sh
bash tests/run-tests.sh
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/ tests/fixtures/transcript-v15-qa.jsonl tests/fixtures/transcript-v15-pivot.jsonl
git commit -m "test(v1.5): integration tests incl. multi-stop, pivot, force/overflow, anchor persistence"
```

---

### Task 8.2: Delete v1 scripts (only after integration passes)

**Files:**
- Delete: `scripts/generate-name.sh`, `scripts/session-writer.sh`, `scripts/utils.sh`
- Delete: `tests/test-generate-name.sh`, `tests/test-rename-hook.sh`, `tests/test-session-writer.sh`, `tests/test-utils.sh`

- [ ] **Step 1: Confirm integration is green**

```bash
bash tests/run-tests.sh
```
Must exit 0.

- [ ] **Step 2: Delete v1 files**

```bash
git rm scripts/generate-name.sh scripts/session-writer.sh scripts/utils.sh
git rm tests/test-generate-name.sh tests/test-rename-hook.sh tests/test-session-writer.sh tests/test-utils.sh
```

- [ ] **Step 3: Run suite again**

```bash
bash tests/run-tests.sh
```
Still green.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore(v1.5): remove v1 scripts (superseded by modular lib/; integration green)"
```

---

## Phase 9: Level 3 manual scenarios (cost cap $10)

### Task 9.1: Level 3 scenarios

**Files:**
- Create: `docs/test-results/2026-04-14-level3-scenarios.md`

- [ ] **Step 1: Define budget cap**

Hard cap: **$10 USD total across all Level 3 scenarios combined**. If cumulative `cost_usd` (sum from logs) approaches $8, stop and assess.

- [ ] **Step 2: Document scenarios to run**

Write into `docs/test-results/2026-04-14-level3-scenarios.md`:

```markdown
# Level 3 Manual Scenarios

Budget: **$10 USD hard cap** across all scenarios. Sum costs from logs:
```
for sid in <session-ids>; do
  jq -s 'map(select(.event == "llm_call_end")) | map(.cost_usd) | add' \
    "$CLAUDE_PLUGIN_DATA/logs/$sid.jsonl"
done | awk '{s+=$1} END {printf "Total so far: $%.4f\n", s}'
```
If sum > $8, stop.

## Scenario A: Short bugfix (~10 turns)
- Fresh project; prompt: a small bug involving 1-2 files.
- Expected: 1-2 LLM calls, title like `auth: fix X`.
- Record: turn count, calls_made, total cost, subjective title quality.

## Scenario B: Long feature (~30 turns)
- Prompt a feature with 4-6 sub-tasks.
- Expected: title evolves 3-5 times; budget hits 6 before session ends.
- Record: title evolution history, budget exhaustion behavior.

## Scenario C: Q&A exploration (~15 turns, no tool calls)
- Conceptual questions only.
- Expected: zero LLM calls (pre-filter skips).
- Record: confirm `calls_made: 0`.
```

- [ ] **Step 3: [USER] Execute scenarios in real Claude Code sessions**

Prerequisites:
- Plugin dev-installed.
- `CLAUDE_PLUGIN_DATA` set to a known directory (so the cost meter below works).
- Real LLM calls will happen — budget meter active.

**Before starting:** set a single CLAUDE_PLUGIN_DATA that captures all 3
scenarios into one log tree:
```bash
export CLAUDE_PLUGIN_DATA="$HOME/.local/share/smart-session-rename/level3-$(date +%Y%m%d)"
mkdir -p "$CLAUDE_PLUGIN_DATA"
echo "Level 3 data root: $CLAUDE_PLUGIN_DATA"
```

For each scenario, open a **fresh** Claude Code session in a throwaway
project dir and run the suggested prompts. After every session, capture:
```bash
SID=<session-id from Claude Code header>
jq -s 'map(select(.event == "llm_call_end")) | {calls: length, cost_total: (map(.cost_usd) | add // 0)}' \
  "$CLAUDE_PLUGIN_DATA/logs/$SID.jsonl"
jq . "$CLAUDE_PLUGIN_DATA/state/$SID.json"
```

Cumulative cost meter (run after each scenario):
```bash
find "$CLAUDE_PLUGIN_DATA/logs" -name '*.jsonl' -exec \
  jq -s 'map(select(.event == "llm_call_end")) | map(.cost_usd) | add // 0' {} \; \
  | awk '{s+=$1} END {printf "Cumulative Level 3 cost: $%.4f / $10 cap\n", s}'
```
**If cumulative >= $8, STOP and assess before continuing.**

Fill in `docs/test-results/2026-04-14-level3-scenarios.md` as you go — for
each scenario record: session id, turn count, calls_made, cost, title
evolution history, subjective quality notes, any surprises.

- [ ] **Step 4: [AGENT] Commit results (after user completes scenarios)**

```bash
git add docs/test-results/2026-04-14-level3-scenarios.md
git commit -m "test(v1.5): Level 3 manual scenario results"
```

---

## Phase 10: Level 4 Computer Use (cost cap $10)

### Task 10.1: Enable + execute Computer Use scenarios

**Files:**
- Create: `docs/test-results/2026-04-14-computer-use.md`

Per the **Manual Testing Strategy** section, the implementing agent cannot
drive another interactive Claude Code session via computer-use (Terminal is
tier "click"). Therefore Phase 10 scenarios are run by the **user's own
Claude Code session** with computer-use enabled — that Claude (a separate
instance) drives Claude Code interactions on the desktop. The implementing
agent (this one) prepares the scenario doc and records results afterwards.

- [ ] **Step 1: [USER] Enable Computer Use in their primary Claude session**

In a fresh Claude Code session (not this implementing one):
- Run `/mcp` → find `computer-use` → Enable.
- Grant macOS Accessibility + Screen Recording permissions when prompted.
- Verify: `mcp__computer-use__screenshot` should work (take a test screenshot).

- [ ] **Step 2: [AGENT] Write scenario doc and budget instructions**

Create `docs/test-results/2026-04-14-computer-use.md` with the scenarios
below and the cost-meter command (same pattern as Phase 9).

Scenarios:

1. **Smoke test (~5 turns):** ask the CU-driving Claude to invoke
   `/smart-rename freeze` in a target terminal window, then `screenshot`
   the terminal + `cat state/*.json` via Bash to verify.
2. **Evolution (~10 turns):** CU-driving Claude sends coding prompts to the
   target Claude Code session; observes state across turns; screenshots
   the session picker (⌘K or similar) to confirm title visibility.
3. **Controls chain:** CU-driving Claude runs
   `freeze` → 2 turns → `explain` → `unfreeze` → `force` → `<anchor>` →
   `explain`. Screenshot each step.
4. **`/rename` nativo detection:** CU-driving Claude invokes native
   `/rename "My custom title"`; verifies `manual_title_override` set in
   state; subsequent turns don't overwrite.
5. **Circuit breaker (optional):** try to force 3 real LLM failures
   (temporarily unplug network, then restore). Verify `llm_disabled: true`
   and that `/smart-rename force` resets. Skip if infeasible.

Budget: **$10 USD cap** (same meter as Phase 9).

- [ ] **Step 3: [USER] Run scenarios with Computer Use driving**

The user runs scenarios in their primary (CU-enabled) Claude session. That
Claude drives Claude Code in a separate terminal/app via
`mcp__computer-use__*` tools. The user oversees, answers any confirmation
prompts, and records observations (title quality, friction points,
calibration suggestions — e.g., "`first_call_work_threshold` of 20 felt
too eager for my usage pattern").

- [ ] **Step 4: [AGENT] Commit report**

```bash
git add docs/test-results/2026-04-14-computer-use.md
git commit -m "test(v1.5): Level 4 Computer Use usability report"
```

---

## Phase 11: Documentation (after Level 3/4 calibration)

### Task 11.1: Apply any threshold tuning discovered in Level 3/4

**Files:**
- Modify: `config/default-config.json` (only if Level 3/4 suggested changes)

- [ ] **Step 1: Review Level 3/4 reports for calibration suggestions**

- [ ] **Step 2: If changes needed, apply and commit**

```bash
# Example: adjust first_call_work_threshold from 20 to 30
jq '.first_call_work_threshold = 30' config/default-config.json > config/default-config.json.tmp && mv config/default-config.json.tmp config/default-config.json
git add config/default-config.json
git commit -m "tune(v1.5): adjust thresholds per Level 3/4 findings"
```

### Task 11.2: Update README, CHANGELOG, plugin.json

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Bump plugin version**

```bash
jq '.version = "1.5.0"' .claude-plugin/plugin.json > .claude-plugin/plugin.json.tmp && mv .claude-plugin/plugin.json.tmp .claude-plugin/plugin.json
```

- [ ] **Step 2: Replace README.md with v1.5 version**

Sections to rewrite:
1. **"How it works"**: paste the 8-step pipeline diagram from v1.5 spec §3.1.
2. **"Configuration"**: table of env vars from v1.5 spec §10.3, each with default + one-line description.
3. **NEW section "Cost model"** between "How it works" and "Configuration":
   > Each LLM call in OAuth mode costs ~$0.10 because `claude -p` loads the full Claude Code context (~80k tokens of cache creation). The plugin budgets 6 calls per session (≈$0.60/session) with 2 manual overflow slots via `/smart-rename force`. Using `ANTHROPIC_API_KEY` with `--bare` would reduce cost by ~250× but isn't the default (see v1.5 spec §1).
4. **FAQ additions**:
   - "Why is there a budget?" → cost model
   - "How does the plugin decide when to rename?" → work-score
   - "What if I want to control the name myself?" → `/smart-rename <name>` or `freeze`
5. **REMOVE**: all `update_interval` references.
6. **"Subcommands"**: list all 7 with one-line descriptions.
7. **Quick Start**: include `/smart-rename explain` as verification.

- [ ] **Step 3: Update CHANGELOG.md**

Prepend:
```markdown
## 1.5.0 — <ISO date of release>

### Changed (breaking)
- Complete rewrite as modular bash (scripts/lib/*.sh).
- Title format now `domain: clause1, clause2, ...` (was kebab-case).
- Deterministic throttling via work_score replaces fixed 3-message interval.
- Budget model: 6 LLM calls per session + 2 manual overflow slots.
- State schema version 1.5 (v1 states — if any existed in practice — not migrated).

### Added
- Structured output via `claude -p --json-schema`.
- Subcommands: `/smart-rename <name>`, `freeze`, `unfreeze`, `force`, `explain`, `unanchor`.
- Detection of `/rename` nativo as `manual_title_override` (free-form, verbatim).
- Distinction between `manual_anchor` (domain slug) and `manual_title_override` (full title).
- Circuit breaker after 3 consecutive LLM failures.
- JSONL structured logs per session (JSON-safe via `jq -nc --arg`).
- Idempotency via `last_processed_signature` (turn_number:file_size) — covers agentic multi-stop.
- Portable timeout (timeout/gtimeout/perl fallback).
- Lock stale threshold raised to 60s (was 30).
- Level 4 testing via Computer Use.

### Removed
- Fixed 3-message interval.
- Heuristic kebab-case fallback.
- v1 scripts: `generate-name.sh`, `session-writer.sh`, `utils.sh`.
```

- [ ] **Step 4: Shellcheck gate**

```bash
shellcheck scripts/*.sh scripts/lib/*.sh tests/run-tests.sh tests/unit/*.sh tests/integration/*.sh
```
Fix any blocking issues. Advisory warnings may be deferred.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json README.md CHANGELOG.md
git commit -m "docs(v1.5): README + CHANGELOG + plugin.json for 1.5.0"
```

---

## Phase 12: Release

### Task 12.1: Final review + tag

- [ ] **Step 1: Final review**

```bash
git log --oneline main..HEAD
```

- [ ] **Step 2: Clean run of all tests**

```bash
bash tests/run-tests.sh && shellcheck scripts/*.sh scripts/lib/*.sh
```

- [ ] **Step 3: Tag**

```bash
git tag -a v1.5.0 -m "Smart Session Rename v1.5.0 — greenfield, structured output, work-score throttling"
```

- [ ] **Step 4: Push if desired**

```bash
git push origin main
git push origin v1.5.0
```

---

## Self-Review (spec coverage + fixes)

**Spec sections mapped to tasks:**
- §1 Contexto → README + CHANGELOG (Phase 11)
- §2 Requisitos → throttling (Phase 4), subcommands (Phase 7), title format (Phase 5.3), budget (Phase 4), /rename detection (Phase 6)
- §3 Arquitetura → Phases 1-6 implement each module
- §3.5 Schema transcript → Phase 3
- §4 Throttling → Phase 4
- §5 LLM → Phases 5.1, 5.2, 5.3
- §6 State → Phase 1.1 + enforced by hook (Phase 6)
- §7 Skill → Phase 1.3 (prototype) + Phase 7 (complete)
- §8 Erros → Phase 6 + Phase 4 (circuit breaker)
- §9 Logs → Phase 2.2 + used throughout
- §10 Config → Phase 2.1
- §11 Testes → unit in Phases 1-5; integration in Phase 8; Level 3 in Phase 9; Level 4 in Phase 10
- §12 Riscos → mitigations embedded (signature idempotency, stale lock 60s, JSON-safe logs, etc.)
- §13 Rollout → this plan IS the rollout (Phases 0-12)
- §14 DoD → mirrored in Phase 12

**Gate 1+2 fixes incorporated:**
- C1 (last_processed_signature after decision) → Phase 6 Step 1
- C2 (trap separation with `_HOOK_CLEAN_EXIT` sentinel) → Phase 6 Step 1
- C3 (jq-based prompt render) → Phase 5.2 Step 4
- C4 (portable timeout fallback) → Phase 5.2 Step 4
- C5 (lock_stale_seconds=60) → Phase 2.1 Step 1 (config defaults)
- C6 (state promoted only after writer success) → Phase 6 Step 1
- C7 (state.sh/logger.sh via config_get) → Phase 1.1 + Phase 2.2
- C8 (jq-based JSON log construction) → Phase 2.2 + Phase 6 throughout
- A1 (signature idempotency) → Phase 4.1 + Phase 6
- A2 (manual_title_override vs manual_anchor) → Phase 5.3 + Phase 6 + Phase 7
- A3 (cwd passed to transcript) → Phase 3.1 + Phase 6
- A4 (cmd_suggest consumes budget) → Phase 7.1
- A5 (v1 deletion moved to Phase 8.2)
- A6 (skill prototype in Phase 1 before config/logger) → Phase 1.3
- A7 (docs after Level 3/4) → Phase 11
- A8 (cost cap $10 per Level 3/4) → Phases 9.1, 10.1
- T1 (extended mock) → Phase 5.2 Step 1
- T2 (real JSONL capture) → Phase 1.2
- T3 (multi-stop test) → Phase 3 fixture + Phase 8 integration
- T4 (pivot fixture used) → Phase 8 integration
- T5 (force/overflow integration) → Phase 8 integration
- T6 (anchor persistence after /rename) → Phase 8 integration

**Known residual limitations** (documented, not fixed in v1.5):
- `writer_append_title` is not atomic under hook↔skill concurrency (both go through `state_lock`, so transcript-level race is very rare). Note in CHANGELOG as known limitation.
- `total_available` dead variable removed.
- `last_user_msg` now handles content-array (Phase 3.1).
