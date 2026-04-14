# Smart Session Rename v1.5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace v1 with a greenfield v1.5 plugin that auto-renames Claude Code sessions using deterministic throttling heuristics + a single Haiku call with structured output.

**Architecture:** Stop hook → modular bash pipeline (config → state → transcript → work-score → decide → LLM → validate → write). All cognition is in a single `claude -p --json-schema` call gated by heuristics (budget 6 calls/session, work-score thresholds). Each module in `scripts/lib/` has one responsibility and its own test file.

**Tech Stack:** bash 5.x + jq 1.6+, `claude` CLI v2.1.85+ (Haiku 4.5), custom shell test harness (same pattern as v1).

**Spec:** `docs/superpowers/specs/2026-04-14-smart-session-rename-v15-design.md`

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
│   ├── test-config.sh
│   ├── test-state.sh
│   ├── test-logger.sh
│   ├── test-transcript.sh
│   ├── test-scorer.sh
│   ├── test-llm.sh
│   ├── test-validate.sh
│   └── test-writer.sh
├── integration/                      # new subdir
│   └── test-end-to-end.sh
├── fixtures/
│   ├── transcript-v15-feature.jsonl  # new
│   ├── transcript-v15-qa.jsonl       # new
│   ├── transcript-v15-pivot.jsonl    # new
│   └── transcript-v15-agentic.jsonl  # new
└── mocks/
    └── claude                        # new (mock binary for integration tests)
```

### Files to DELETE (v1 replaced by v1.5)

- `scripts/generate-name.sh` — functionality now split across `lib/transcript.sh`, `lib/llm.sh`, `lib/validate.sh`
- `scripts/session-writer.sh` — becomes `lib/writer.sh`
- `scripts/utils.sh` — becomes `lib/config.sh` + `lib/logger.sh`
- `tests/test-generate-name.sh` — replaced by unit tests per module
- `tests/test-rename-hook.sh` — replaced by `integration/test-end-to-end.sh`
- `tests/test-session-writer.sh` — replaced by `unit/test-writer.sh`
- `tests/test-utils.sh` — replaced by `unit/test-config.sh` + `unit/test-logger.sh`

### Files to MODIFY

- `.claude-plugin/plugin.json` — bump version to 1.5.0, update description if needed
- `config/default-config.json` — replace with v1.5 defaults (Section 10.1 of spec)
- `hooks/hooks.json` — keep as-is (points to scripts/rename-hook.sh which remains the entry point)
- `skills/smart-rename/SKILL.md` — rewrite for v1.5 subcommands (Section 7.2 of spec)
- `tests/run-tests.sh` — update to walk `unit/` and `integration/` subdirs
- `README.md` — update for v1.5 behavior
- `CHANGELOG.md` — add 1.5.0 entry

### Pre-work (one-off before Phase 1)

The user has uncommitted changes in `scripts/generate-name.sh` and `scripts/rename-hook.sh` from before this session. Those are learnings that informed the v1.5 spec but are not used directly in v1.5. The user decides at Phase 0 whether to commit them as v1 history or discard.

---

## Phase 0: Prepare workspace

### Task 0.1: Handle pre-existing v1 modifications

**Files:**
- Read state: `scripts/generate-name.sh`, `scripts/rename-hook.sh` (uncommitted modifications)

- [ ] **Step 1: Check uncommitted changes**

```bash
git status --short scripts/
```
Expected output includes:
```
 M scripts/generate-name.sh
 M scripts/rename-hook.sh
```

- [ ] **Step 2: Ask user how to handle them**

Present two options:
- (a) Commit them as v1 history preservation: `git add scripts/generate-name.sh scripts/rename-hook.sh && git commit -m "chore: preserve v1 learnings on JSONL format and portable lock before v1.5 rewrite"`
- (b) Discard: `git checkout scripts/generate-name.sh scripts/rename-hook.sh`

Do whichever the user picks. The v1.5 work below overwrites or deletes these files regardless, but history is preserved differently in each branch.

- [ ] **Step 3: Verify clean working tree for scripts/**

```bash
git status --short scripts/
```
Expected: empty output (no modifications).

---

## Phase 1: Foundation modules (config, state, logger)

### Task 1.1: Create `lib/config.sh` with tests

**Files:**
- Create: `scripts/lib/config.sh`
- Create: `tests/unit/test-config.sh`
- Modify: `config/default-config.json` (replace with v1.5 defaults)

- [ ] **Step 1: Replace `config/default-config.json`**

Write:
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
  "lock_stale_seconds": 30,
  "llm_timeout_seconds": 25,

  "log_level": "info",
  "max_clauses": 5,
  "max_domain_chars": 30,
  "max_user_msg_chars": 500,
  "max_assistant_chars": 500
}
```

- [ ] **Step 2: Create `tests/unit/test-config.sh` with failing assertions**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/config.sh"

PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "  ✓ $desc"
    ((PASS++)) || true
  else
    echo "  ✗ $desc: expected '$expected', got '$actual'"
    ((FAIL++)) || true
  fi
}

echo "=== config.sh tests ==="

# Isolate test env
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
unset SMART_RENAME_ENABLED SMART_RENAME_MODEL SMART_RENAME_BUDGET_CALLS \
      SMART_RENAME_OVERFLOW_SLOTS SMART_RENAME_FIRST_THRESHOLD \
      SMART_RENAME_ONGOING_THRESHOLD SMART_RENAME_REATTACH_INTERVAL \
      SMART_RENAME_CB_THRESHOLD SMART_RENAME_LLM_TIMEOUT \
      SMART_RENAME_LOG_LEVEL 2>/dev/null || true

echo "-- defaults from config/default-config.json --"
config_load
assert_eq "default enabled" "true" "$(config_get enabled)"
assert_eq "default model" "claude-haiku-4-5" "$(config_get model)"
assert_eq "default max_budget_calls" "6" "$(config_get max_budget_calls)"
assert_eq "default first_call_work_threshold" "20" "$(config_get first_call_work_threshold)"
assert_eq "default ongoing_work_threshold" "40" "$(config_get ongoing_work_threshold)"
assert_eq "default reattach_interval" "10" "$(config_get reattach_interval)"
assert_eq "default overflow_manual_slots" "2" "$(config_get overflow_manual_slots)"

echo "-- env var overrides --"
export SMART_RENAME_BUDGET_CALLS=10
export SMART_RENAME_FIRST_THRESHOLD=15
config_load
assert_eq "env overrides budget" "10" "$(config_get max_budget_calls)"
assert_eq "env overrides first_threshold" "15" "$(config_get first_call_work_threshold)"
unset SMART_RENAME_BUDGET_CALLS SMART_RENAME_FIRST_THRESHOLD

echo "-- user config file overrides defaults --"
mkdir -p "$CLAUDE_PLUGIN_DATA"
cat > "$CLAUDE_PLUGIN_DATA/config.json" <<EOF
{"max_budget_calls": 4, "ongoing_work_threshold": 50}
EOF
config_load
assert_eq "file overrides budget" "4" "$(config_get max_budget_calls)"
assert_eq "file overrides ongoing" "50" "$(config_get ongoing_work_threshold)"
assert_eq "file keeps default for unset" "20" "$(config_get first_call_work_threshold)"

echo "-- env > file > defaults precedence --"
export SMART_RENAME_BUDGET_CALLS=99
config_load
assert_eq "env beats file" "99" "$(config_get max_budget_calls)"
unset SMART_RENAME_BUDGET_CALLS

rm -rf "$CLAUDE_PLUGIN_DATA"

echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

Make it executable: `chmod +x tests/unit/test-config.sh`

- [ ] **Step 3: Run test to verify it fails (config.sh does not exist yet)**

```bash
bash tests/unit/test-config.sh
```
Expected: error about missing file `scripts/lib/config.sh`, or undefined function `config_load`.

- [ ] **Step 4: Create `scripts/lib/config.sh`**

```bash
#!/usr/bin/env bash
# lib/config.sh — config loading with precedence: env > user file > defaults
# Sourced by other scripts.

# shellcheck disable=SC2034

_CONFIG_LOADED=""
declare -gA _CONFIG_VALUES

# Maps config key → env var name
_config_env_var() {
  case "$1" in
    enabled)                       echo "SMART_RENAME_ENABLED" ;;
    model)                         echo "SMART_RENAME_MODEL" ;;
    max_budget_calls)              echo "SMART_RENAME_BUDGET_CALLS" ;;
    overflow_manual_slots)         echo "SMART_RENAME_OVERFLOW_SLOTS" ;;
    first_call_work_threshold)     echo "SMART_RENAME_FIRST_THRESHOLD" ;;
    ongoing_work_threshold)        echo "SMART_RENAME_ONGOING_THRESHOLD" ;;
    reattach_interval)             echo "SMART_RENAME_REATTACH_INTERVAL" ;;
    circuit_breaker_threshold)     echo "SMART_RENAME_CB_THRESHOLD" ;;
    lock_stale_seconds)            echo "SMART_RENAME_LOCK_STALE" ;;
    llm_timeout_seconds)           echo "SMART_RENAME_LLM_TIMEOUT" ;;
    log_level)                     echo "SMART_RENAME_LOG_LEVEL" ;;
    *)                             echo "" ;;
  esac
}

config_load() {
  local defaults_file user_file
  defaults_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/config/default-config.json"
  user_file="${CLAUDE_PLUGIN_DATA:-}/config.json"

  _CONFIG_VALUES=()

  # 1. Load defaults
  if [[ -f "$defaults_file" ]]; then
    while IFS=$'\t' read -r key val; do
      _CONFIG_VALUES["$key"]="$val"
    done < <(jq -r 'to_entries[] | "\(.key)\t\(.value)"' "$defaults_file" 2>/dev/null || true)
  fi

  # 2. Overlay user file if present
  if [[ -n "${CLAUDE_PLUGIN_DATA:-}" && -f "$user_file" ]]; then
    while IFS=$'\t' read -r key val; do
      _CONFIG_VALUES["$key"]="$val"
    done < <(jq -r 'to_entries[] | "\(.key)\t\(.value)"' "$user_file" 2>/dev/null || true)
  fi

  # 3. Overlay env vars
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
  if [[ -z "$_CONFIG_LOADED" ]]; then
    config_load
  fi
  echo "${_CONFIG_VALUES[$key]:-}"
}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
bash tests/unit/test-config.sh
```
Expected:
```
=== config.sh tests ===
...
Result: 10 passed, 0 failed
```

- [ ] **Step 6: Commit**

```bash
git add scripts/lib/config.sh tests/unit/test-config.sh config/default-config.json
git commit -m "feat(v1.5): add lib/config.sh with env > file > defaults precedence"
```

---

### Task 1.2: Create `lib/logger.sh` with tests

**Files:**
- Create: `scripts/lib/logger.sh`
- Create: `tests/unit/test-logger.sh`

- [ ] **Step 1: Create `tests/unit/test-logger.sh` with failing assertions**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/logger.sh"

PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "  ✓ $desc"; ((PASS++)) || true
  else
    echo "  ✗ $desc: expected '$expected', got '$actual'"; ((FAIL++)) || true
  fi
}

assert_contains() {
  local desc="$1" needle="$2" haystack="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    echo "  ✓ $desc"; ((PASS++)) || true
  else
    echo "  ✗ $desc: '$haystack' does not contain '$needle'"; ((FAIL++)) || true
  fi
}

echo "=== logger.sh tests ==="

export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
SESSION_ID="test-session-abc"

echo "-- emits valid JSONL with expected fields --"
log_event info score_update "test-session-abc" '{"delta":6,"acc":18.5,"turn":14}'
logfile="$CLAUDE_PLUGIN_DATA/logs/test-session-abc.jsonl"
[[ -f "$logfile" ]] && echo "  ✓ log file created" && ((PASS++)) || { echo "  ✗ log file missing"; ((FAIL++)) || true; }

first_line="$(head -1 "$logfile")"
assert_contains "log contains event" '"event":"score_update"' "$first_line"
assert_contains "log contains turn" '"turn":14' "$first_line"
assert_contains "log contains level" '"level":"info"' "$first_line"
assert_contains "log contains ts" '"ts":"' "$first_line"

echo "-- each log line is valid JSON --"
if echo "$first_line" | jq . >/dev/null 2>&1; then
  echo "  ✓ line is valid JSON"; ((PASS++)) || true
else
  echo "  ✗ line is not valid JSON: $first_line"; ((FAIL++)) || true
fi

echo "-- level filter respects SMART_RENAME_LOG_LEVEL --"
rm -f "$logfile"
export SMART_RENAME_LOG_LEVEL=warn
log_event info suppressed_event "test-session-abc" '{}'
[[ ! -f "$logfile" || ! -s "$logfile" ]] && echo "  ✓ info suppressed at warn level" && ((PASS++)) || { echo "  ✗ info was not suppressed"; ((FAIL++)) || true; }
log_event warn kept_event "test-session-abc" '{}'
[[ -s "$logfile" ]] && grep -q kept_event "$logfile" && echo "  ✓ warn kept at warn level" && ((PASS++)) || { echo "  ✗ warn was suppressed"; ((FAIL++)) || true; }
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
Expected: fail with missing file.

- [ ] **Step 3: Create `scripts/lib/logger.sh`**

```bash
#!/usr/bin/env bash
# lib/logger.sh — structured JSONL logging per session.

_LOG_LEVELS_SUPPRESS="" # computed on first use

_log_level_rank() {
  case "$1" in
    debug) echo 0 ;;
    info)  echo 1 ;;
    warn)  echo 2 ;;
    error) echo 3 ;;
    *)     echo 1 ;; # default info
  esac
}

log_event() {
  # Args: level event_type session_id data_json
  local level="$1" event="$2" session_id="$3" data="${4:-\{\}}"

  local cur_level="${SMART_RENAME_LOG_LEVEL:-info}"
  if [[ "$(_log_level_rank "$level")" -lt "$(_log_level_rank "$cur_level")" ]]; then
    return 0
  fi

  local base_dir="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}"
  local log_dir="$base_dir/logs"
  mkdir -p "$log_dir"
  local log_file="$log_dir/$session_id.jsonl"

  local ts
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  # Merge data object with ts, level, event — data wins if overlaps (shouldn't)
  jq -nc \
    --arg ts "$ts" \
    --arg level "$level" \
    --arg event "$event" \
    --argjson data "$data" \
    '{ts: $ts, level: $level, event: $event} + $data' \
    >> "$log_file" 2>/dev/null || true
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
bash tests/unit/test-logger.sh
```
Expected: all checks pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/logger.sh tests/unit/test-logger.sh
git commit -m "feat(v1.5): add lib/logger.sh with JSONL structured logs and level filter"
```

---

### Task 1.3: Create `lib/state.sh` with tests (load/save atomic + locking)

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
assert_true() { local d="$1" cond="$2"; [[ "$cond" == "true" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d"; ((FAIL++)) || true; }; }

echo "=== state.sh tests ==="
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
SID="sess-1"

echo "-- state_load with missing file returns empty state --"
state=$(state_load "$SID")
assert_eq "version empty on new state" "" "$(echo "$state" | jq -r '.version // ""')"

echo "-- state_save writes atomically --"
state_save "$SID" '{"version":"1.5","calls_made":3}'
state=$(state_load "$SID")
assert_eq "saved version" "1.5" "$(echo "$state" | jq -r '.version')"
assert_eq "saved calls_made" "3" "$(echo "$state" | jq -r '.calls_made')"

echo "-- state_save uses temp + mv (no partial write on interruption) --"
# verify no *.tmp files left behind
tmp_count=$(ls "$CLAUDE_PLUGIN_DATA/state/"*.tmp* 2>/dev/null | wc -l | tr -d ' ')
assert_eq "no leftover tmp files" "0" "$tmp_count"

echo "-- state_lock / state_unlock --"
state_lock "$SID" && assert_true "lock acquired" "true" || assert_true "lock acquired" "false"
[[ -d "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir" ]] && echo "  ✓ lock dir exists" && ((PASS++)) || { echo "  ✗ lock dir missing"; ((FAIL++)) || true; }

echo "-- second lock attempt fails quickly --"
start=$(date +%s)
if state_lock "$SID" 2>/dev/null; then
  echo "  ✗ second lock should fail"; ((FAIL++)) || true
else
  elapsed=$(($(date +%s) - start))
  [[ $elapsed -le 3 ]] && echo "  ✓ second lock failed within 3s (got ${elapsed}s)" && ((PASS++)) || { echo "  ✗ lock took too long: ${elapsed}s"; ((FAIL++)) || true; }
fi

state_unlock "$SID"
[[ ! -d "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir" ]] && echo "  ✓ lock released" && ((PASS++)) || { echo "  ✗ lock still held"; ((FAIL++)) || true; }

echo "-- stale lock is cleaned --"
mkdir -p "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir"
# backdate it 40 seconds (exceeds default 30s stale threshold)
touch -t "$(date -v-40S +"%Y%m%d%H%M.%S" 2>/dev/null || date -u -d '40 seconds ago' +"%Y%m%d%H%M.%S")" "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir" 2>/dev/null || true
state_lock "$SID" && assert_true "stale lock cleaned" "true" || assert_true "stale lock cleaned" "false"
state_unlock "$SID"

echo "-- corrupted state renames to .corrupt.bak and resets --"
echo "not valid json {" > "$CLAUDE_PLUGIN_DATA/state/$SID.json"
state=$(state_load "$SID")
assert_eq "corrupted resets to empty" "" "$(echo "$state" | jq -r '.version // ""')"
[[ -f "$CLAUDE_PLUGIN_DATA/state/$SID.json.corrupt.bak" ]] && echo "  ✓ corrupt backup saved" && ((PASS++)) || { echo "  ✗ corrupt backup missing"; ((FAIL++)) || true; }

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bash tests/unit/test-state.sh
```
Expected: fail with missing file.

- [ ] **Step 3: Create `scripts/lib/state.sh`**

```bash
#!/usr/bin/env bash
# lib/state.sh — session state JSON load/save + locking

_state_file() {
  local sid="$1"
  local base="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}"
  mkdir -p "$base/state"
  echo "$base/state/$sid.json"
}

_state_lockdir() {
  echo "$(_state_file "$1").lockdir"
}

state_load() {
  local sid="$1"
  local f; f="$(_state_file "$sid")"
  if [[ ! -f "$f" ]]; then
    echo "{}"
    return 0
  fi
  if ! jq . "$f" >/dev/null 2>&1; then
    # corrupted — back up and return empty
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
  stale_seconds="${SMART_RENAME_LOCK_STALE:-30}"
  max_wait=2
  waited=0

  # Stale check before attempting
  if [[ -d "$lockdir" ]]; then
    local age
    # mtime in epoch seconds (macOS vs Linux)
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
Expected: all checks pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/state.sh tests/unit/test-state.sh
git commit -m "feat(v1.5): add lib/state.sh with atomic save, portable lock, corrupt recovery"
```

---

## Phase 2: Skill prototype (validate mechanism early)

### Task 2.1: Minimal smart-rename-cli.sh with only `freeze`/`unfreeze`

This phase validates that the Claude-in-session can execute plugin scripts and manipulate state, before investing in full 7 subcommands.

**Files:**
- Create: `scripts/smart-rename-cli.sh` (minimal)
- Modify: `skills/smart-rename/SKILL.md` (minimal instructions for freeze/unfreeze)

- [ ] **Step 1: Create minimal `scripts/smart-rename-cli.sh`**

```bash
#!/usr/bin/env bash
# smart-rename-cli.sh — skill subcommand dispatcher (Phase 2: minimal)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/config.sh"
source "$SCRIPT_DIR/lib/state.sh"
source "$SCRIPT_DIR/lib/logger.sh"

session_id_from_env_or_transcript() {
  if [[ -n "${CLAUDE_SESSION_ID:-}" ]]; then
    echo "$CLAUDE_SESSION_ID"
    return 0
  fi
  if [[ -n "${1:-}" && -f "$1" ]]; then
    basename "$1" .jsonl
    return 0
  fi
  echo ""
  return 1
}

cmd="${1:-}"
shift || true

case "$cmd" in
  freeze)
    sid="$(session_id_from_env_or_transcript "${1:-}")"
    [[ -z "$sid" ]] && { echo "ERROR: cannot determine session id"; exit 1; }
    state_lock "$sid" || { echo "ERROR: could not lock"; exit 1; }
    trap 'state_unlock "$sid"' EXIT
    state=$(state_load "$sid")
    new_state=$(echo "$state" | jq '.frozen = true | .updated_at = (now | todate)')
    state_save "$sid" "$new_state"
    log_event info freeze_toggled "$sid" '{"frozen":true}'
    echo "Smart rename: FROZEN for session $sid"
    ;;
  unfreeze)
    sid="$(session_id_from_env_or_transcript "${1:-}")"
    [[ -z "$sid" ]] && { echo "ERROR: cannot determine session id"; exit 1; }
    state_lock "$sid" || { echo "ERROR: could not lock"; exit 1; }
    trap 'state_unlock "$sid"' EXIT
    state=$(state_load "$sid")
    new_state=$(echo "$state" | jq '.frozen = false | .updated_at = (now | todate)')
    state_save "$sid" "$new_state"
    log_event info freeze_toggled "$sid" '{"frozen":false}'
    echo "Smart rename: UNFROZEN for session $sid"
    ;;
  *)
    echo "Phase 2 prototype — only freeze/unfreeze supported."
    echo "Usage: $0 freeze|unfreeze [transcript_path]"
    exit 1
    ;;
esac
```

Make executable: `chmod +x scripts/smart-rename-cli.sh`

- [ ] **Step 2: Rewrite `skills/smart-rename/SKILL.md` (minimal Phase 2 version)**

```markdown
---
name: smart-rename
description: Manage the smart-session-rename plugin for the current session. Phase 2 prototype supports freeze/unfreeze.
---

# /smart-rename (v1.5 prototype)

When the user invokes `/smart-rename` with a subcommand, run the matching command below via the Bash tool and report the output.

## Determining session id

The environment variable `$CLAUDE_SESSION_ID` is usually set. If it isn't, derive the session id from the transcript path (the filename without `.jsonl`).

## Subcommands (Phase 2 minimal)

### `/smart-rename freeze`

Run:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh freeze "$CLAUDE_TRANSCRIPT_PATH"
```

### `/smart-rename unfreeze`

Run:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh unfreeze "$CLAUDE_TRANSCRIPT_PATH"
```

For other subcommands, respond: "Not yet implemented (Phase 2 prototype)."
```

- [ ] **Step 3: Manual smoke test**

Launch an interactive Claude Code session in a test project with the plugin installed (local dev install works). In that session, run:

```
/smart-rename freeze
```

Expected:
- Claude executes `smart-rename-cli.sh freeze` via Bash
- Reports "Smart rename: FROZEN for session <id>"
- Check state file: `cat $CLAUDE_PLUGIN_DATA/state/<id>.json | jq .`
- Should show `"frozen": true`

Then:
```
/smart-rename unfreeze
```
Expected: state shows `"frozen": false`.

- [ ] **Step 4: Document results**

Write findings to `docs/test-results/2026-04-14-skill-prototype.md`:
- Did `$CLAUDE_SESSION_ID` exist?
- Did the Bash tool execute the script?
- Any race conditions with the Stop hook observed?
- Session id derivation from transcript path worked?

If prototype succeeds: proceed to Phase 3. If not: adjust mechanism (e.g., pass session_id explicitly, different skill invocation pattern) before continuing.

- [ ] **Step 5: Commit**

```bash
git add scripts/smart-rename-cli.sh skills/smart-rename/SKILL.md docs/test-results/
git commit -m "feat(v1.5): add Phase 2 skill prototype (freeze/unfreeze) to validate mechanism"
```

---

## Phase 3: Transcript parser and scorer (the heart of v1.5)

### Task 3.1: Create `lib/transcript.sh` with tests

**Files:**
- Create: `scripts/lib/transcript.sh`
- Create: `tests/unit/test-transcript.sh`
- Create: `tests/fixtures/transcript-v15-feature.jsonl`
- Create: `tests/fixtures/transcript-v15-agentic.jsonl`

- [ ] **Step 1: Create fixture `tests/fixtures/transcript-v15-feature.jsonl`**

```jsonl
{"type":"user","message":{"role":"user","content":"Add rate limiting to the auth endpoints"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"I'll add rate limiting using express-rate-limit for the login and signup endpoints."},{"type":"tool_use","id":"tu1","name":"Read","input":{"file_path":"src/auth/login.ts"}},{"type":"tool_use","id":"tu2","name":"Read","input":{"file_path":"src/auth/signup.ts"}},{"type":"tool_use","id":"tu3","name":"Edit","input":{"file_path":"src/auth/rate-limit.ts","old_string":"","new_string":"import rateLimit from 'express-rate-limit';\n..."}},{"type":"tool_use","id":"tu4","name":"Bash","input":{"command":"npm test"}}]}}
```

- [ ] **Step 2: Create fixture `tests/fixtures/transcript-v15-agentic.jsonl` (multi-turn with complex agentic loop)**

```jsonl
{"type":"user","message":{"role":"user","content":"Fix the JWT expiry bug in auth module"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Let me investigate the JWT expiry logic."},{"type":"tool_use","id":"a1","name":"Read","input":{"file_path":"src/auth/jwt.ts"}},{"type":"text","text":"I see the issue. The expiry check uses seconds instead of milliseconds."},{"type":"tool_use","id":"a2","name":"Edit","input":{"file_path":"src/auth/jwt.ts","old_string":"Date.now() > exp","new_string":"Date.now() > exp * 1000"}},{"type":"tool_use","id":"a3","name":"Bash","input":{"command":"npm test -- auth"}},{"type":"text","text":"Tests pass. The fix is complete."}]}}
{"type":"user","message":{"role":"user","content":"Also add a test for the edge case where exp is 0"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Adding that edge case test."},{"type":"tool_use","id":"b1","name":"Edit","input":{"file_path":"tests/auth/jwt.test.ts","old_string":"","new_string":"test('handles exp=0', () => { ... })"}},{"type":"tool_use","id":"b2","name":"Bash","input":{"command":"npm test -- auth"}},{"type":"text","text":"Done, test passes."}]}}
```

- [ ] **Step 3: Create `tests/unit/test-transcript.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/transcript.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

FIXTURE_DIR="$SCRIPT_DIR/../fixtures"

echo "=== transcript.sh tests ==="

echo "-- single-turn feature fixture --"
result=$(transcript_parse_current_turn "$FIXTURE_DIR/transcript-v15-feature.jsonl" "[]")
assert_eq "turn_number" "1" "$(echo "$result" | jq -r '.turn_number')"
assert_eq "user_msg substring" "Add rate limiting" "$(echo "$result" | jq -r '.user_msg' | cut -c1-17)"
assert_eq "user_word_count" "7" "$(echo "$result" | jq -r '.user_word_count')"
assert_eq "tool_call_count" "4" "$(echo "$result" | jq -r '.tool_call_count')"
assert_eq "new files has rate-limit" "true" "$(echo "$result" | jq '[.new_files_this_turn[] | select(contains("rate-limit"))] | length > 0')"

echo "-- agentic multi-turn fixture parses only LAST turn --"
result=$(transcript_parse_current_turn "$FIXTURE_DIR/transcript-v15-agentic.jsonl" "[]")
assert_eq "turn_number is 2" "2" "$(echo "$result" | jq -r '.turn_number')"
assert_eq "user_msg is second message" "Also add" "$(echo "$result" | jq -r '.user_msg' | cut -c1-8)"
assert_eq "tool_call_count is 2 (only last turn)" "2" "$(echo "$result" | jq -r '.tool_call_count')"

echo "-- new_files_this_turn excludes previously seen --"
# Pass previous active files so new files are only those not in that list
result=$(transcript_parse_current_turn "$FIXTURE_DIR/transcript-v15-agentic.jsonl" '["src/auth/jwt.ts"]')
# jwt.ts was seen before; tests/auth/jwt.test.ts is new
assert_eq "new file is test only" "1" "$(echo "$result" | jq -r '.new_files_this_turn | length')"

echo "-- domain_guess from file paths --"
assert_eq "domain_guess auth" "auth" "$(echo "$result" | jq -r '.domain_guess')"

echo "-- missing transcript returns error-shaped JSON --"
result=$(transcript_parse_current_turn "/nonexistent/path.jsonl" "[]" || true)
assert_eq "error field present" "missing_transcript" "$(echo "$result" | jq -r '.error // ""')"

echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 4: Run test to verify it fails**

```bash
bash tests/unit/test-transcript.sh
```
Expected: fail with missing `transcript.sh`.

- [ ] **Step 5: Create `scripts/lib/transcript.sh`**

```bash
#!/usr/bin/env bash
# lib/transcript.sh — parse Claude Code JSONL for the current turn.
# A "turn" = user message + all following assistant blocks until end of file.

# Reads last ~200KB of JSONL and returns the final turn's signals.
# Args: transcript_path, previous_active_files_json (array)
# Stdout: JSON with fields documented in v1.5 spec §3.5
transcript_parse_current_turn() {
  local path="$1" prev_files_json="${2:-[]}"

  if [[ ! -r "$path" ]]; then
    echo '{"error":"missing_transcript"}'
    return 0
  fi

  # Read last 200KB to capture full current turn (margin over 64KB window)
  local tail_content
  tail_content=$(tail -c 204800 "$path" 2>/dev/null || cat "$path")

  # Parse events from tail. Use jq to stream.
  # Identify turns by counting user messages from the start.
  # Since we tailed, we might cut a line; skip first line if it doesn't parse.
  local events
  events=$(echo "$tail_content" | jq -c 'select(. != null)' 2>/dev/null | tail -n +1 || true)

  # Total user turns in the file (for turn_number)
  local total_turns
  total_turns=$(jq -s 'map(select(.type == "user")) | length' "$path" 2>/dev/null || echo 0)

  # Last user message (start of current turn)
  local last_user_msg
  last_user_msg=$(jq -rs 'map(select(.type == "user")) | last // {} | .message.content // ""' "$path" 2>/dev/null || echo "")

  local user_word_count
  user_word_count=$(echo "$last_user_msg" | tr -s '[:space:]' '\n' | grep -c . || echo 0)

  # All assistant blocks from the last turn: find index of last user in file, then take everything after
  # Use jq to extract content arrays of assistant messages AFTER the last user
  local assistant_content
  assistant_content=$(jq -rs '
    (. | map(select(.type == "user")) | length) as $uc |
    . as $all |
    (reduce range(0; $all | length) as $i (-1; if $all[$i].type == "user" then $i else . end)) as $last_user_idx |
    $all[($last_user_idx+1):] | map(select(.type == "assistant"))
  ' "$path" 2>/dev/null || echo '[]')

  # tool_use blocks across all assistant messages of the current turn
  local tool_call_count
  tool_call_count=$(echo "$assistant_content" | jq '
    [.[] | .message.content // [] | .[] | select(.type == "tool_use")] | length
  ' 2>/dev/null || echo 0)

  # All file paths touched via tool_use inputs that contain file_path
  local all_files
  all_files=$(echo "$assistant_content" | jq -c '
    [.[] | .message.content // [] | .[] | select(.type == "tool_use") | .input.file_path // empty] | unique
  ' 2>/dev/null || echo '[]')

  # New files this turn = all_files minus prev_files
  local new_files
  new_files=$(jq -cn --argjson all "$all_files" --argjson prev "$prev_files_json" \
    '$all - $prev' 2>/dev/null || echo '[]')

  # Assistant concatenated text
  local assistant_text
  assistant_text=$(echo "$assistant_content" | jq -r '
    [.[] | .message.content // [] | .[] | select(.type == "text") | .text] | join(" ")
  ' 2>/dev/null || echo "")

  # Assistant sentence count (approximation: count . ! ? outside code blocks)
  local assistant_sentence_count
  assistant_sentence_count=$(echo "$assistant_text" | sed 's/```[^`]*```//g' | grep -oE '[.!?]' | wc -l | tr -d ' ' || echo 0)

  # domain_guess: most common top-level directory among all_files (or cwd basename fallback)
  local domain_guess
  domain_guess=$(echo "$all_files" | jq -r '
    [.[] | split("/")[0]] | group_by(.) | map({k:.[0], n:length}) | sort_by(-.n) | first.k // empty
  ' 2>/dev/null)
  if [[ -z "$domain_guess" || "$domain_guess" == "null" ]]; then
    # look deeper: second-level dir (e.g., src/auth/* → auth)
    domain_guess=$(echo "$all_files" | jq -r '
      [.[] | split("/") | .[1] // empty | select(. != "")] | group_by(.) | map({k:.[0], n:length}) | sort_by(-.n) | first.k // empty
    ' 2>/dev/null)
  fi
  if [[ -z "$domain_guess" || "$domain_guess" == "null" ]]; then
    domain_guess="$(basename "${PWD:-/}")"
  fi

  # Branch (best-effort)
  local branch
  branch="$(git -C "${PWD:-/}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"

  local tool_names
  tool_names=$(echo "$assistant_content" | jq -c '
    [.[] | .message.content // [] | .[] | select(.type == "tool_use") | .name]
  ' 2>/dev/null || echo '[]')

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
      branch: $br
    }'
}
```

- [ ] **Step 6: Run test to verify it passes**

```bash
bash tests/unit/test-transcript.sh
```
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add scripts/lib/transcript.sh tests/unit/test-transcript.sh tests/fixtures/transcript-v15-feature.jsonl tests/fixtures/transcript-v15-agentic.jsonl
git commit -m "feat(v1.5): add lib/transcript.sh parser for current turn extraction"
```

---

### Task 3.2: Create `lib/scorer.sh` with tests

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
# 3 tool_calls + 2 new_files + 100 user_words → 3 + 6 + 1.0 = 10
turn_data='{"tool_call_count":3,"new_files_this_turn":["a","b"],"user_word_count":100}'
delta=$(scorer_compute_delta "$turn_data")
assert_eq "delta=10 for 3+6+1" "10" "$delta"

# zero case
delta=$(scorer_compute_delta '{"tool_call_count":0,"new_files_this_turn":[],"user_word_count":0}')
assert_eq "delta=0 for zero inputs" "0" "$delta"

echo "-- should_call_llm: frozen → SKIP --"
state='{"frozen":true,"title_struct":null,"accumulated_score":100,"calls_made":0,"overflow_used":0,"failure_count":0,"llm_disabled":false,"force_next":false}'
decision=$(scorer_should_call_llm "$state" 0 | jq -r '.decision')
reason=$(scorer_should_call_llm "$state" 0 | jq -r '.reason')
assert_eq "frozen skips" "skip" "$decision"
assert_eq "frozen reason" "frozen" "$reason"

echo "-- force_next → CALL --"
state='{"frozen":false,"title_struct":null,"accumulated_score":0,"calls_made":0,"overflow_used":0,"failure_count":0,"llm_disabled":false,"force_next":true}'
decision=$(scorer_should_call_llm "$state" 0 | jq -r '.decision')
assert_eq "force triggers" "call" "$decision"

echo "-- llm_disabled → SKIP --"
state='{"frozen":false,"title_struct":null,"accumulated_score":100,"calls_made":0,"overflow_used":0,"failure_count":3,"llm_disabled":true,"force_next":false}'
decision=$(scorer_should_call_llm "$state" 0 | jq -r '.decision')
assert_eq "disabled skips" "skip" "$decision"

echo "-- budget exhausted (6 of 6 used, 2 overflow used) → SKIP --"
state='{"frozen":false,"title_struct":{"domain":"x"},"accumulated_score":100,"calls_made":6,"overflow_used":2,"failure_count":0,"llm_disabled":false,"force_next":false}'
decision=$(scorer_should_call_llm "$state" 0 | jq -r '.decision')
assert_eq "budget exhausted" "skip" "$decision"

echo "-- first call threshold (null title_struct) --"
state='{"frozen":false,"title_struct":null,"accumulated_score":15,"calls_made":0,"overflow_used":0,"failure_count":0,"llm_disabled":false,"force_next":false}'
decision=$(scorer_should_call_llm "$state" 0 | jq -r '.decision')
assert_eq "below first threshold skips" "skip" "$decision"

state='{"frozen":false,"title_struct":null,"accumulated_score":20,"calls_made":0,"overflow_used":0,"failure_count":0,"llm_disabled":false,"force_next":false}'
decision=$(scorer_should_call_llm "$state" 0 | jq -r '.decision')
assert_eq "at first threshold calls" "call" "$decision"

echo "-- ongoing threshold (has title_struct) --"
state='{"frozen":false,"title_struct":{"domain":"x"},"accumulated_score":39,"calls_made":1,"overflow_used":0,"failure_count":0,"llm_disabled":false,"force_next":false}'
decision=$(scorer_should_call_llm "$state" 0 | jq -r '.decision')
assert_eq "below ongoing threshold skips" "skip" "$decision"

state='{"frozen":false,"title_struct":{"domain":"x"},"accumulated_score":40,"calls_made":1,"overflow_used":0,"failure_count":0,"llm_disabled":false,"force_next":false}'
decision=$(scorer_should_call_llm "$state" 0 | jq -r '.decision')
assert_eq "at ongoing threshold calls" "call" "$decision"

echo "-- idempotency: same turn number returns 'skip_idempotent' --"
state='{"frozen":false,"title_struct":{"domain":"x"},"accumulated_score":100,"calls_made":1,"overflow_used":0,"failure_count":0,"llm_disabled":false,"force_next":false,"last_processed_turn":5}'
decision=$(scorer_should_call_llm "$state" 5 | jq -r '.decision')
reason=$(scorer_should_call_llm "$state" 5 | jq -r '.reason')
assert_eq "idempotent skip" "skip" "$decision"
assert_eq "idempotent reason" "already_processed" "$reason"

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bash tests/unit/test-scorer.sh
```
Expected: fail with missing `scorer.sh`.

- [ ] **Step 3: Create `scripts/lib/scorer.sh`**

```bash
#!/usr/bin/env bash
# lib/scorer.sh — work-score computation and call/skip decision.

# Args: turn_data_json
# Stdout: numeric delta
scorer_compute_delta() {
  local turn="$1"
  # delta = tool_calls*1 + new_files*3 + user_words*0.01
  echo "$turn" | jq -r '
    ((.tool_call_count // 0) + ((.new_files_this_turn // []) | length) * 3 + ((.user_word_count // 0) * 0.01))
    | if . == (. | floor) then (. | tostring) else . end
  ' 2>/dev/null | awk '{ printf "%g\n", $1 }'
}

# Args: state_json, current_turn_number
# Stdout: {"decision":"call"|"skip","reason":"<string>"}
scorer_should_call_llm() {
  local state="$1" current_turn="$2"

  # Idempotency check
  local last_processed
  last_processed=$(echo "$state" | jq -r '.last_processed_turn // -1')
  if [[ "$current_turn" -ge 0 && "$last_processed" == "$current_turn" ]]; then
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
    # Allow force even past budget if overflow slots remain
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

  local total_used=$(( calls_made + overflow_used ))
  local total_available=$(( max_calls + overflow_slots ))
  if [[ "$total_used" -ge "$max_calls" ]]; then
    echo '{"decision":"skip","reason":"budget_exhausted"}'
    return 0
  fi

  if [[ "$has_title" == "false" ]]; then
    # First call path
    if awk -v a="$acc" -v t="$first_thr" 'BEGIN { exit !(a >= t) }'; then
      echo '{"decision":"call","reason":"first_call_threshold"}'
      return 0
    fi
    echo '{"decision":"skip","reason":"below_first_threshold"}'
    return 0
  fi

  # Ongoing
  if awk -v a="$acc" -v t="$ongoing_thr" 'BEGIN { exit !(a >= t) }'; then
    echo '{"decision":"call","reason":"ongoing_threshold"}'
    return 0
  fi
  echo '{"decision":"skip","reason":"below_ongoing_threshold"}'
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
bash tests/unit/test-scorer.sh
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/scorer.sh tests/unit/test-scorer.sh
git commit -m "feat(v1.5): add lib/scorer.sh — work-score + call/skip decision logic"
```

---

## Phase 4: LLM pipeline (llm, validate, writer, prompts)

### Task 4.1: Create `prompts/generation.md`

**Files:**
- Create: `scripts/prompts/generation.md`

- [ ] **Step 1: Write `scripts/prompts/generation.md`**

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
- Produce {domain, clauses[]} matching the JSON schema.
- `domain`: short slug (1-3 words) naming the subject area (e.g., "auth", "deploy-pipeline").
- If MANUAL ANCHOR is set and non-empty, use it exactly as `domain`.
- `clauses`: 1 to 5 items, each `[verb] [concrete entity]` (e.g., "fix jwt expiry", "add tests").
  - Avoid generic jargon ("implementation", "enhancement", "optimization").
  - Prefer active verbs. Entities should be concrete (file, module, behavior).
- If nothing substantial changed versus CURRENT TITLE, return the same structure anyway (the plugin deduplicates identical titles without writing).
- Keep the domain stable across turns unless the subject clearly changed.
```

- [ ] **Step 2: Commit**

```bash
git add scripts/prompts/generation.md
git commit -m "feat(v1.5): add prompts/generation.md (iterable LLM prompt template)"
```

---

### Task 4.2: Create `lib/llm.sh` with tests (mock claude)

**Files:**
- Create: `scripts/lib/llm.sh`
- Create: `tests/unit/test-llm.sh`
- Create: `tests/mocks/claude` (mock binary for tests)

- [ ] **Step 1: Create `tests/mocks/claude` (mock binary)**

```bash
#!/usr/bin/env bash
# Mock claude CLI for tests. Reads MOCK_CLAUDE_RESPONSE env var as the JSON output.
# Exits 0 on success, non-zero if MOCK_CLAUDE_FAIL=1.

if [[ "${MOCK_CLAUDE_FAIL:-0}" == "1" ]]; then
  echo "[]" >&2
  exit 1
fi

cat <<EOF
${MOCK_CLAUDE_RESPONSE:-[{"type":"result","is_error":false,"duration_ms":100,"total_cost_usd":0.001,"structured_output":{"domain":"test","clauses":["do thing"]}}]}
EOF
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

export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
config_load

# Put mock first in PATH
export PATH="$SCRIPT_DIR/../mocks:$PATH"

echo "=== llm.sh tests ==="

echo "-- successful call parses structured_output --"
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"duration_ms":100,"total_cost_usd":0.001,"structured_output":{"domain":"auth","clauses":["fix jwt","add tests"]}}]'
ctx='{"CURRENT_TITLE":"none","MANUAL_ANCHOR":"","BRANCH":"main","DOMAIN_GUESS":"auth","RECENT_FILES":"src/auth/jwt.ts","USER_MSG":"fix jwt bug","ASSISTANT_SUMMARY":"patched expiry","RECENT_TURNS":"turn 1: ..."}'
result=$(llm_generate_title "$ctx")
assert_eq "domain parsed" "auth" "$(echo "$result" | jq -r '.domain')"
assert_eq "clauses count" "2" "$(echo "$result" | jq -r '.clauses | length')"
assert_eq "no error field" "null" "$(echo "$result" | jq -r '.error')"

echo "-- call failure returns error --"
export MOCK_CLAUDE_FAIL=1
result=$(llm_generate_title "$ctx" || true)
assert_eq "error set on failure" "call_failed" "$(echo "$result" | jq -r '.error // ""')"
unset MOCK_CLAUDE_FAIL

echo "-- missing structured_output returns error --"
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false}]'
result=$(llm_generate_title "$ctx" || true)
assert_eq "error on missing output" "invalid_output" "$(echo "$result" | jq -r '.error // ""')"

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 3: Run test to verify it fails**

```bash
bash tests/unit/test-llm.sh
```
Expected: missing `llm.sh`.

- [ ] **Step 4: Create `scripts/lib/llm.sh`**

```bash
#!/usr/bin/env bash
# lib/llm.sh — wrapper around claude -p with --json-schema structured output.

_LLM_JSON_SCHEMA='{
  "type":"object",
  "properties":{
    "domain":{"type":"string","minLength":1,"maxLength":30},
    "clauses":{"type":"array","items":{"type":"string","minLength":2,"maxLength":50},"minItems":1,"maxItems":5}
  },
  "required":["domain","clauses"],
  "additionalProperties":false
}'

_render_prompt() {
  local ctx_json="$1"
  local template_file
  template_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/prompts/generation.md"
  [[ ! -f "$template_file" ]] && { echo ""; return 1; }
  local template
  template=$(cat "$template_file")

  # Substitute ${VAR} placeholders with jq values from ctx_json
  local keys
  keys=$(echo "$ctx_json" | jq -r 'keys[]')
  while IFS= read -r key; do
    local val
    val=$(echo "$ctx_json" | jq -r --arg k "$key" '.[$k] // ""')
    # Escape for sed
    local esc
    esc=$(printf '%s' "$val" | sed -e 's/[\/&]/\\&/g')
    template=$(echo "$template" | sed "s/\${$key}/$esc/g")
  done <<< "$keys"

  printf '%s' "$template"
}

llm_generate_title() {
  local ctx_json="$1"
  local prompt
  prompt=$(_render_prompt "$ctx_json") || { echo '{"error":"prompt_template_missing"}'; return 1; }

  local model timeout
  model=$(config_get model)
  timeout=$(config_get llm_timeout_seconds)

  local raw
  if ! raw=$(timeout "$timeout" claude -p \
    --model "$model" \
    --output-format json \
    --no-session-persistence \
    --json-schema "$_LLM_JSON_SCHEMA" \
    "$prompt" 2>/dev/null); then
    echo '{"error":"call_failed"}'
    return 1
  fi

  # Check is_error
  local is_error
  is_error=$(echo "$raw" | jq -r '[.[] | select(.type == "result")] | first | .is_error // false')
  if [[ "$is_error" == "true" ]]; then
    echo '{"error":"call_failed"}'
    return 1
  fi

  # Extract structured_output
  local output
  output=$(echo "$raw" | jq -c '[.[] | select(.type == "result")] | first | .structured_output // empty')
  if [[ -z "$output" || "$output" == "null" ]]; then
    echo '{"error":"invalid_output"}'
    return 1
  fi

  # Extract cost/duration for logging
  local cost duration
  cost=$(echo "$raw" | jq -r '[.[] | select(.type == "result")] | first | .total_cost_usd // 0')
  duration=$(echo "$raw" | jq -r '[.[] | select(.type == "result")] | first | .duration_ms // 0')

  # Return structured_output plus meta
  echo "$output" | jq --arg cost "$cost" --arg dur "$duration" \
    '. + {_cost_usd: ($cost | tonumber), _duration_ms: ($dur | tonumber)}'
}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
bash tests/unit/test-llm.sh
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/lib/llm.sh tests/mocks/claude tests/unit/test-llm.sh
git commit -m "feat(v1.5): add lib/llm.sh with --json-schema structured output"
```

---

### Task 4.3: Create `lib/validate.sh` with tests

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

export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
config_load

echo "=== validate.sh tests ==="

echo "-- simple render --"
out='{"domain":"auth","clauses":["fix jwt expiry","add tests"]}'
state='{"rendered_title":"","manual_anchor":null}'
result=$(validate_and_render "$out" "$state")
assert_eq "render" "auth: fix jwt expiry, add tests" "$(echo "$result" | jq -r '.rendered_title')"
assert_eq "status ok" "ok" "$(echo "$result" | jq -r '.status')"

echo "-- identical title returns skip --"
state='{"rendered_title":"auth: fix jwt expiry, add tests","manual_anchor":null}'
result=$(validate_and_render "$out" "$state")
assert_eq "skip on identical" "skip_identical" "$(echo "$result" | jq -r '.status')"

echo "-- manual_anchor overrides domain --"
state='{"rendered_title":"","manual_anchor":"fernando-custom"}'
result=$(validate_and_render "$out" "$state")
assert_eq "anchor applied" "fernando-custom: fix jwt expiry, add tests" "$(echo "$result" | jq -r '.rendered_title')"

echo "-- dedupe identical clauses (case/whitespace) --"
out='{"domain":"auth","clauses":["fix jwt","  fix jwt  ","FIX JWT","add tests"]}'
state='{"rendered_title":"","manual_anchor":null}'
result=$(validate_and_render "$out" "$state")
assert_eq "deduped" "auth: fix jwt, add tests" "$(echo "$result" | jq -r '.rendered_title')"

echo "-- empty clauses → invalid --"
out='{"domain":"auth","clauses":[]}'
result=$(validate_and_render "$out" "$state")
assert_eq "invalid empty clauses" "invalid" "$(echo "$result" | jq -r '.status')"

echo "-- empty domain → invalid --"
out='{"domain":"","clauses":["a"]}'
result=$(validate_and_render "$out" "$state")
assert_eq "invalid empty domain" "invalid" "$(echo "$result" | jq -r '.status')"

echo "-- error-shaped input passes through --"
out='{"error":"call_failed"}'
result=$(validate_and_render "$out" "$state")
assert_eq "error passes through" "error" "$(echo "$result" | jq -r '.status')"

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bash tests/unit/test-validate.sh
```
Expected: missing validate.sh.

- [ ] **Step 3: Create `scripts/lib/validate.sh`**

```bash
#!/usr/bin/env bash
# lib/validate.sh — validate LLM output and render title.

# Args: llm_output_json, state_json
# Stdout: {"status":"ok"|"skip_identical"|"invalid"|"error", "rendered_title":"...", "title_struct":{...}}
validate_and_render() {
  local output="$1" state="$2"

  # Pass-through error
  local err
  err=$(echo "$output" | jq -r '.error // ""')
  if [[ -n "$err" ]]; then
    echo "$output" | jq -c --arg e "$err" '{status:"error", error:$e}'
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

  # Truncate domain if too long
  domain="${domain:0:$max_domain_chars}"

  # Apply manual_anchor override
  local manual_anchor
  manual_anchor=$(echo "$state" | jq -r '.manual_anchor // ""')
  if [[ -n "$manual_anchor" && "$manual_anchor" != "null" ]]; then
    domain="$manual_anchor"
  fi

  # Dedupe clauses: trim + lowercase + collapse ws
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

  # Render title
  local joined
  joined=$(echo "$deduped" | jq -r 'join(", ")')
  local rendered="$domain: $joined"

  # Compare with state.rendered_title
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

- [ ] **Step 4: Run test to verify it passes**

```bash
bash tests/unit/test-validate.sh
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/validate.sh tests/unit/test-validate.sh
git commit -m "feat(v1.5): add lib/validate.sh — schema check, anchor override, dedupe, render"
```

---

### Task 4.4: Create `lib/writer.sh` with tests

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

echo "-- appends custom-title record --"
writer_append_title "$tmp" "auth: fix jwt"
last=$(tail -1 "$tmp")
assert_eq "type is custom-title" "custom-title" "$(echo "$last" | jq -r '.type')"
assert_eq "title is set" "auth: fix jwt" "$(echo "$last" | jq -r '.customTitle')"

echo "-- appending second title adds another line --"
writer_append_title "$tmp" "auth: fix jwt, add tests"
count=$(grep -c '"type":"custom-title"' "$tmp" || true)
assert_eq "two records" "2" "$count"

echo "-- get_last_custom_title reads latest --"
last_title=$(writer_get_last_custom_title "$tmp")
assert_eq "last title" "auth: fix jwt, add tests" "$last_title"

echo "-- no custom-title returns empty --"
empty_file=$(mktemp)
echo '{"type":"user","message":{"role":"user","content":"x"}}' > "$empty_file"
last_title=$(writer_get_last_custom_title "$empty_file")
assert_eq "empty when no custom-title" "" "$last_title"

echo "-- refuses to write if transcript missing --"
if writer_append_title "/nonexistent/path.jsonl" "x" 2>/dev/null; then
  echo "  ✗ should have failed"; ((FAIL++)) || true
else
  echo "  ✓ failed as expected"; ((PASS++)) || true
fi

rm -f "$tmp" "$empty_file"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bash tests/unit/test-writer.sh
```
Expected: missing writer.sh.

- [ ] **Step 3: Create `scripts/lib/writer.sh`**

```bash
#!/usr/bin/env bash
# lib/writer.sh — append custom-title records to session JSONL.

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

- [ ] **Step 4: Run test to verify it passes**

```bash
bash tests/unit/test-writer.sh
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/writer.sh tests/unit/test-writer.sh
git commit -m "feat(v1.5): add lib/writer.sh — append custom-title, read last"
```

---

## Phase 5: Hook orchestration

### Task 5.1: Rewrite `scripts/rename-hook.sh` as modular orchestrator

**Files:**
- Rewrite (replace existing content): `scripts/rename-hook.sh`
- Delete: `scripts/generate-name.sh`, `scripts/session-writer.sh`, `scripts/utils.sh`
- Delete: `tests/test-generate-name.sh`, `tests/test-rename-hook.sh`, `tests/test-session-writer.sh`, `tests/test-utils.sh`
- Modify: `tests/run-tests.sh`

- [ ] **Step 1: Delete v1 scripts and tests**

```bash
git rm scripts/generate-name.sh scripts/session-writer.sh scripts/utils.sh
git rm tests/test-generate-name.sh tests/test-rename-hook.sh tests/test-session-writer.sh tests/test-utils.sh
```

- [ ] **Step 2: Update `tests/run-tests.sh` to walk subdirs**

Replace with:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOTAL_PASS=0
TOTAL_FAIL=0

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

- [ ] **Step 3: Rewrite `scripts/rename-hook.sh`**

```bash
#!/usr/bin/env bash
# rename-hook.sh — v1.5 Stop hook orchestrator.
# Input: stdin JSON {session_id, transcript_path, cwd}.
# Always exits 0; never blocks the session.

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

# Global error handler — always exit 0
trap 'log_event error hook_crashed "${SESSION_ID:-unknown}" "{\"line\":$LINENO}"; exit 0' ERR

# --- 1. Parse input ---
INPUT_RAW="$(cat)"
SESSION_ID="$(echo "$INPUT_RAW" | jq -r '.session_id // empty')"
TRANSCRIPT_PATH="$(echo "$INPUT_RAW" | jq -r '.transcript_path // empty')"
CWD="$(echo "$INPUT_RAW" | jq -r '.cwd // empty')"

[[ -z "$SESSION_ID" || -z "$TRANSCRIPT_PATH" ]] && exit 0

# Check prerequisites
command -v jq >/dev/null 2>&1 || { log_event error missing_dep "$SESSION_ID" '{"dep":"jq"}'; exit 0; }
command -v claude >/dev/null 2>&1 || { log_event error missing_dep "$SESSION_ID" '{"dep":"claude"}'; exit 0; }

[[ ! -r "$TRANSCRIPT_PATH" ]] && { log_event warn transcript_missing "$SESSION_ID" "{}"; exit 0; }

config_load
[[ "$(config_get enabled)" != "true" ]] && exit 0

# --- 2. Lock + load state ---
if ! state_lock "$SESSION_ID"; then
  log_event info lock_contention "$SESSION_ID" "{}"
  exit 0
fi
trap 'state_unlock "$SESSION_ID"; log_event error hook_crashed "$SESSION_ID" "{\"line\":$LINENO}"; exit 0' ERR EXIT

STATE="$(state_load "$SESSION_ID")"

# --- 3. Detect /rename nativo ---
LAST_JSONL_TITLE="$(writer_get_last_custom_title "$TRANSCRIPT_PATH")"
LAST_PLUGIN_TITLE="$(echo "$STATE" | jq -r '.last_plugin_written_title // ""')"
if [[ -n "$LAST_JSONL_TITLE" && "$LAST_JSONL_TITLE" != "$LAST_PLUGIN_TITLE" ]]; then
  STATE=$(echo "$STATE" | jq --arg t "$LAST_JSONL_TITLE" '
    .manual_anchor = $t
    | .rendered_title = $t
    | .last_plugin_written_title = $t
  ')
  log_event info manual_rename_detected "$SESSION_ID" "{\"new_title\":\"$LAST_JSONL_TITLE\"}"
fi

# --- 4. Parse transcript ---
PREV_FILES=$(echo "$STATE" | jq -c '.active_files_recent // []')
TURN=$(transcript_parse_current_turn "$TRANSCRIPT_PATH" "$PREV_FILES")
TURN_NUM=$(echo "$TURN" | jq -r '.turn_number // 0')

# --- 5. Idempotency guard + work score update ---
LAST_PROCESSED=$(echo "$STATE" | jq -r '.last_processed_turn // -1')
if [[ "$LAST_PROCESSED" == "$TURN_NUM" ]]; then
  log_event debug idempotent_skip "$SESSION_ID" "{\"turn\":$TURN_NUM}"
  exit 0
fi

DELTA=$(scorer_compute_delta "$TURN")
STATE=$(echo "$STATE" | jq \
  --argjson turn "$TURN" \
  --argjson d "$DELTA" \
  --argjson t "$TURN_NUM" '
  .accumulated_score = ((.accumulated_score // 0) + $d)
  | .last_processed_turn = $t
  | .domain_guess = ($turn.domain_guess // .domain_guess)
  | .active_files_recent = (
      ((.active_files_recent // []) + ($turn.all_files_touched // []))
      | unique | .[0:20]
    )
  | .branch = ($turn.branch // .branch // "")
  | .updated_at = (now | todate)
  | .version = "1.5"
')

log_event debug score_update "$SESSION_ID" "$(jq -nc --argjson d "$DELTA" --argjson acc "$(echo "$STATE" | jq -r '.accumulated_score')" --argjson t "$TURN_NUM" '{delta:$d, acc:$acc, turn:$t}')"

# --- 6. Decide ---
DECISION_JSON=$(scorer_should_call_llm "$STATE" "$TURN_NUM")
DECISION=$(echo "$DECISION_JSON" | jq -r '.decision')
REASON=$(echo "$DECISION_JSON" | jq -r '.reason')

REATTACH_INTERVAL=$(config_get reattach_interval)
CUR_TITLE=$(echo "$STATE" | jq -r '.rendered_title // ""')

log_event info llm_decision "$SESSION_ID" "$(jq -nc --arg d "$DECISION" --arg r "$REASON" '{decision:$d, reason:$r}')"

if [[ "$DECISION" == "skip" ]]; then
  # Periodic re-attach to preserve 64KB window
  if [[ -n "$CUR_TITLE" ]] && (( TURN_NUM % REATTACH_INTERVAL == 0 )); then
    writer_append_title "$TRANSCRIPT_PATH" "$CUR_TITLE" && \
      log_event info title_reattached "$SESSION_ID" "$(jq -nc --arg t "$CUR_TITLE" '{title:$t}')"
  fi
  state_save "$SESSION_ID" "$STATE"
  exit 0
fi

# --- 7. Call LLM ---
CALLS_MADE=$(echo "$STATE" | jq -r '.calls_made // 0')
OVERFLOW_USED=$(echo "$STATE" | jq -r '.overflow_used // 0')
MAX_CALLS=$(config_get max_budget_calls)

# If past budget and using overflow, bump overflow
if [[ "$CALLS_MADE" -ge "$MAX_CALLS" ]]; then
  STATE=$(echo "$STATE" | jq '.overflow_used = (.overflow_used + 1) | .force_next = false')
else
  STATE=$(echo "$STATE" | jq '.calls_made = (.calls_made + 1) | .force_next = false')
fi

# Build context
CTX=$(jq -nc \
  --arg t "$CUR_TITLE" \
  --arg a "$(echo "$STATE" | jq -r '.manual_anchor // ""')" \
  --arg br "$(echo "$STATE" | jq -r '.branch // ""')" \
  --arg dg "$(echo "$STATE" | jq -r '.domain_guess // ""')" \
  --arg rf "$(echo "$STATE" | jq -r '(.active_files_recent // []) | .[:5] | join(", ")')" \
  --arg um "$(echo "$TURN" | jq -r '.user_msg // ""')" \
  --arg as "$(echo "$TURN" | jq -r '.assistant_text // "" | .[:500]')" \
  --arg rt "$(echo "$STATE" | jq -r '(.transition_history // []) | map("turn " + (.turn|tostring) + ": " + .title) | join("\n")')" \
  '{CURRENT_TITLE:$t, MANUAL_ANCHOR:$a, BRANCH:$br, DOMAIN_GUESS:$dg, RECENT_FILES:$rf, USER_MSG:$um, ASSISTANT_SUMMARY:$as, RECENT_TURNS:$rt}'
)

log_event info llm_call_start "$SESSION_ID" "$(echo "$STATE" | jq -c '{calls_made, overflow_used}')"

LLM_OUTPUT=$(llm_generate_title "$CTX" || echo '{"error":"call_failed"}')
COST=$(echo "$LLM_OUTPUT" | jq -r '._cost_usd // 0')
DURATION=$(echo "$LLM_OUTPUT" | jq -r '._duration_ms // 0')

log_event info llm_call_end "$SESSION_ID" "$(jq -nc --arg c "$COST" --arg d "$DURATION" --argjson o "$LLM_OUTPUT" '{cost_usd:($c|tonumber), duration_ms:($d|tonumber), output:$o}')"

# --- 8. Validate + write ---
LLM_ERR=$(echo "$LLM_OUTPUT" | jq -r '.error // ""')
if [[ -n "$LLM_ERR" ]]; then
  # failure: increment counter, maybe trip breaker
  NEW_FAIL=$(( $(echo "$STATE" | jq -r '.failure_count // 0') + 1 ))
  CB_THR=$(config_get circuit_breaker_threshold)
  STATE=$(echo "$STATE" | jq --argjson n "$NEW_FAIL" --argjson thr "$CB_THR" '
    .failure_count = $n
    | .llm_disabled = ($n >= $thr)
  ')
  if (( NEW_FAIL >= CB_THR )); then
    log_event warn circuit_breaker_tripped "$SESSION_ID" "$(jq -nc --argjson n "$NEW_FAIL" '{failure_count:$n}')"
  fi
  state_save "$SESSION_ID" "$STATE"
  exit 0
fi

# Success: reset failure count
STATE=$(echo "$STATE" | jq '.failure_count = 0 | .llm_disabled = false')

VALIDATED=$(validate_and_render "$LLM_OUTPUT" "$STATE")
STATUS=$(echo "$VALIDATED" | jq -r '.status')

if [[ "$STATUS" == "ok" ]]; then
  TITLE=$(echo "$VALIDATED" | jq -r '.rendered_title')
  TS=$(echo "$VALIDATED" | jq -c '.title_struct')
  writer_append_title "$TRANSCRIPT_PATH" "$TITLE"
  # Append to transition_history (cap 3)
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
elif [[ "$STATUS" == "skip_identical" ]]; then
  STATE=$(echo "$STATE" | jq '.accumulated_score = 0')
  log_event info title_skipped "$SESSION_ID" '{"reason":"identical"}'
else
  log_event warn title_invalid "$SESSION_ID" "$VALIDATED"
fi

state_save "$SESSION_ID" "$STATE"
exit 0
```

Make executable: `chmod +x scripts/rename-hook.sh`

- [ ] **Step 4: Remove the obsolete v1 test runner concerns by running full test suite**

```bash
bash tests/run-tests.sh
```
Expected: all 8 unit tests pass (test-config, test-state, test-logger, test-transcript, test-scorer, test-llm, test-validate, test-writer).

- [ ] **Step 5: Commit**

```bash
git add scripts/rename-hook.sh tests/run-tests.sh
git rm scripts/generate-name.sh scripts/session-writer.sh scripts/utils.sh tests/test-generate-name.sh tests/test-rename-hook.sh tests/test-session-writer.sh tests/test-utils.sh 2>/dev/null || true
git commit -m "feat(v1.5): rewrite rename-hook.sh as modular orchestrator; remove v1 scripts"
```

---

## Phase 6: Complete the skill (remaining subcommands)

### Task 6.1: Complete `scripts/smart-rename-cli.sh` with all subcommands

**Files:**
- Rewrite: `scripts/smart-rename-cli.sh` (expands Phase 2 prototype to all 7 subcommands)
- Modify: `skills/smart-rename/SKILL.md`

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
  # shellcheck disable=SC2064
  trap "state_unlock $sid" EXIT
  "$@"
}

usage() {
  cat <<EOF
Usage: /smart-rename [args]

Subcommands:
  /smart-rename                 — suggest a rename based on session analysis (consumes 1 budget slot)
  /smart-rename <name>          — set a manual anchor (domain fixed to <name>)
  /smart-rename freeze          — pause automatic updates
  /smart-rename unfreeze        — resume automatic updates
  /smart-rename force           — force LLM call on next Stop hook
  /smart-rename explain         — show current state and history
  /smart-rename unanchor        — clear manual anchor
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
  log_event info force_triggered "$sid" "{}"
  echo "Force flag set; will evaluate on next Stop hook."
}

cmd_anchor() {
  local sid="$1" name="$2" transcript="$3"
  local st; st=$(state_load "$sid")
  # Determine new rendered_title: keep existing clauses but replace domain
  local clauses; clauses=$(echo "$st" | jq -c '.title_struct.clauses // []')
  local n; n=$(echo "$clauses" | jq 'length')
  local title
  if [[ "$n" -eq 0 ]]; then
    title="$name"
  else
    local joined; joined=$(echo "$clauses" | jq -r 'join(", ")')
    title="$name: $joined"
  fi
  state_save "$sid" "$(echo "$st" | jq --arg a "$name" --arg t "$title" '
    .manual_anchor = $a
    | .rendered_title = $t
    | .title_struct.domain = $a
    | .last_plugin_written_title = $t
    | .updated_at = (now | todate)
  ')"
  if [[ -f "$transcript" ]]; then
    writer_append_title "$transcript" "$title" || true
  fi
  log_event info manual_anchor_set "$sid" "$(jq -nc --arg a "$name" '{anchor:$a}')"
  echo "Anchor set: $name (title: \"$title\")"
}

cmd_unanchor() {
  local sid="$1"
  local st; st=$(state_load "$sid")
  state_save "$sid" "$(echo "$st" | jq '.manual_anchor = null | .updated_at = (now | todate)')"
  log_event info manual_anchor_set "$sid" '{"anchor":null}'
  echo "Anchor cleared."
}

cmd_explain() {
  local sid="$1"
  config_load
  local st; st=$(state_load "$sid")
  local max_calls overflow_slots first_thr ongoing_thr
  max_calls=$(config_get max_budget_calls)
  overflow_slots=$(config_get overflow_manual_slots)
  first_thr=$(config_get first_call_work_threshold)
  ongoing_thr=$(config_get ongoing_work_threshold)

  local title domain anchor frozen force llm_dis fc calls overflow acc
  title=$(echo "$st" | jq -r '.rendered_title // "(not yet named)"')
  domain=$(echo "$st" | jq -r '.title_struct.domain // "—"')
  anchor=$(echo "$st" | jq -r '.manual_anchor // "—"')
  frozen=$(echo "$st" | jq -r '.frozen // false')
  force=$(echo "$st" | jq -r '.force_next // false')
  llm_dis=$(echo "$st" | jq -r '.llm_disabled // false')
  fc=$(echo "$st" | jq -r '.failure_count // 0')
  calls=$(echo "$st" | jq -r '.calls_made // 0')
  overflow=$(echo "$st" | jq -r '.overflow_used // 0')
  acc=$(echo "$st" | jq -r '.accumulated_score // 0')

  local has_title; has_title=$(echo "$st" | jq -r 'if .title_struct then "true" else "false" end')
  local next_thr; next_thr=$first_thr
  [[ "$has_title" == "true" ]] && next_thr=$ongoing_thr

  cat <<EOF
Título atual: $title
Domínio: $domain (anchor: $anchor)
Estado: $([ "$frozen" = "true" ] && echo "congelado" || echo "ativo")$([ "$force" = "true" ] && echo "; force próximo turno" || echo "")

Budget: $calls/$max_calls chamadas usadas, $((max_calls - calls)) restantes · overflow $overflow/$overflow_slots
Circuit breaker: $([ "$llm_dis" = "true" ] && echo "ATIVO (plugin desabilitado)" || echo "OK ($fc falhas consecutivas)")
Work score acumulado: $acc (próximo call em ≥$next_thr)

Últimas transições:
EOF
  echo "$st" | jq -r '
    (.transition_history // [])[]
    | "  turno \(.turn)  → \(.title)  (\(.reason))"
  ' 2>/dev/null || echo "  (sem histórico ainda)"

  echo ""
  echo "Último evento do log:"
  local log_file="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}/logs/$sid.jsonl"
  if [[ -f "$log_file" ]]; then
    tail -1 "$log_file"
  else
    echo "  (sem log ainda)"
  fi
}

cmd_suggest() {
  local sid="$1" transcript="$2"
  # Run one LLM call bypassing scorer; present suggestion; do not auto-apply.
  local st; st=$(state_load "$sid")
  local prev_files; prev_files=$(echo "$st" | jq -c '.active_files_recent // []')
  local turn; turn=$(transcript_parse_current_turn "$transcript" "$prev_files")

  local ctx
  ctx=$(jq -nc \
    --arg t "$(echo "$st" | jq -r '.rendered_title // ""')" \
    --arg a "$(echo "$st" | jq -r '.manual_anchor // ""')" \
    --arg br "$(echo "$turn" | jq -r '.branch // ""')" \
    --arg dg "$(echo "$turn" | jq -r '.domain_guess // ""')" \
    --arg rf "$(echo "$turn" | jq -r '.all_files_touched | .[:5] | join(", ")')" \
    --arg um "$(echo "$turn" | jq -r '.user_msg // ""')" \
    --arg as "$(echo "$turn" | jq -r '.assistant_text // "" | .[:500]')" \
    --arg rt "" \
    '{CURRENT_TITLE:$t, MANUAL_ANCHOR:$a, BRANCH:$br, DOMAIN_GUESS:$dg, RECENT_FILES:$rf, USER_MSG:$um, ASSISTANT_SUMMARY:$as, RECENT_TURNS:$rt}')

  local out; out=$(llm_generate_title "$ctx" || echo '{"error":"call_failed"}')
  local err; err=$(echo "$out" | jq -r '.error // ""')
  if [[ -n "$err" ]]; then
    echo "LLM call failed: $err"
    return 1
  fi

  local validated; validated=$(validate_and_render "$out" "$st")
  local title; title=$(echo "$validated" | jq -r '.rendered_title')
  echo "Suggested title: $title"
  echo "To apply: re-run with \`/smart-rename $title\` or leave automation to evolve it."
}

# --- Dispatcher ---
cmd="${1:-}"; shift || true

case "$cmd" in
  "" )
    # /smart-rename alone → suggest
    transcript="${1:-}"
    sid="$(session_id_from_args "$transcript")"
    [[ -z "$sid" ]] && { echo "ERROR: cannot determine session id"; exit 1; }
    with_lock "$sid" cmd_suggest "$sid" "$transcript"
    ;;
  freeze)   sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_freeze "$sid" ;;
  unfreeze) sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_unfreeze "$sid" ;;
  force)    sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_force "$sid" ;;
  unanchor) sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_unanchor "$sid" ;;
  explain)  sid="$(session_id_from_args "${1:-}")"; cmd_explain "$sid" ;;
  help|-h|--help) usage ;;
  *)
    # Anchor mode: /smart-rename <name> [transcript]
    name="$cmd"
    transcript="${1:-}"
    sid="$(session_id_from_args "$transcript")"
    [[ -z "$sid" ]] && { echo "ERROR: cannot determine session id"; exit 1; }
    with_lock "$sid" cmd_anchor "$sid" "$name" "$transcript"
    ;;
esac
```

- [ ] **Step 2: Rewrite `skills/smart-rename/SKILL.md` for full v1.5**

```markdown
---
name: smart-rename
description: Manage the smart-session-rename plugin for the current session — suggest, anchor, freeze, force, explain.
---

# /smart-rename (v1.5)

When the user invokes `/smart-rename [args]`, run the matching command below via the Bash tool and report the output verbatim. Pass `$CLAUDE_TRANSCRIPT_PATH` as the last argument; it lets the CLI derive the session id if `$CLAUDE_SESSION_ID` is not set.

## Subcommands

### `/smart-rename` (no args) — suggest

Analyze the current session and suggest a title without applying it automatically.
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh "" "$CLAUDE_TRANSCRIPT_PATH"
```

### `/smart-rename <name>` — set anchor

Fix the domain to `<name>`. Automation may still add clauses, but the prefix/domain stays.
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh "<name>" "$CLAUDE_TRANSCRIPT_PATH"
```

### `/smart-rename freeze` / `/smart-rename unfreeze`

Pause or resume automatic updates.
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh freeze "$CLAUDE_TRANSCRIPT_PATH"
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh unfreeze "$CLAUDE_TRANSCRIPT_PATH"
```

### `/smart-rename force`

Force a full LLM reevaluation on the next Stop hook (consumes one budget slot, or an overflow slot if budget is exhausted).
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh force "$CLAUDE_TRANSCRIPT_PATH"
```

### `/smart-rename explain`

Show current state: title, domain, anchor, budget usage, circuit breaker, work score, transitions.
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh explain "$CLAUDE_TRANSCRIPT_PATH"
```

### `/smart-rename unanchor`

Clear the manual anchor; automation retakes control of the domain.
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/smart-rename-cli.sh unanchor "$CLAUDE_TRANSCRIPT_PATH"
```

## Error handling

If the CLI exits non-zero, report the error message verbatim to the user. Do not retry automatically.
```

- [ ] **Step 3: Manual smoke test**

In an interactive Claude Code session:
```
/smart-rename freeze
/smart-rename explain
/smart-rename unfreeze
/smart-rename my-test-anchor
/smart-rename explain
/smart-rename unanchor
```

Verify each command produces expected output and updates state as documented.

- [ ] **Step 4: Commit**

```bash
git add scripts/smart-rename-cli.sh skills/smart-rename/SKILL.md
git commit -m "feat(v1.5): complete skill with all 7 subcommands"
```

---

## Phase 7: Integration tests, plugin metadata, docs

### Task 7.1: Integration test — end-to-end with mocked claude

**Files:**
- Create: `tests/integration/test-end-to-end.sh`
- Create: `tests/fixtures/transcript-v15-qa.jsonl` (Q&A session fixture)
- Create: `tests/fixtures/transcript-v15-pivot.jsonl` (pivot fixture)

- [ ] **Step 1: Create Q&A fixture `tests/fixtures/transcript-v15-qa.jsonl`**

```jsonl
{"type":"user","message":{"role":"user","content":"What does useEffect cleanup do in React?"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"The cleanup function in useEffect runs before the effect re-executes or when the component unmounts. It's used for clearing timers, canceling subscriptions, or removing event listeners."}]}}
```

- [ ] **Step 2: Create pivot fixture `tests/fixtures/transcript-v15-pivot.jsonl`**

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

# Isolate test env
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
# Mock claude in PATH
export PATH="$SCRIPT_DIR/../mocks:$PATH"

run_hook() {
  local transcript="$1" session_id="$2"
  jq -nc --arg sid "$session_id" --arg tp "$transcript" --arg cwd "$PWD" \
    '{session_id:$sid, transcript_path:$tp, cwd:$cwd}' | \
    bash "$HOOK"
}

echo "=== end-to-end integration tests ==="

echo "-- Q&A fixture: low work_score → no LLM call --"
tmp_qa=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-qa.jsonl" "$tmp_qa"
run_hook "$tmp_qa" "sess-qa"
state_qa=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-qa.json")
assert_eq "no LLM call for Q&A" "0" "$(echo "$state_qa" | jq -r '.calls_made // 0')"

echo "-- Feature fixture: above threshold → LLM call happens --"
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"duration_ms":200,"total_cost_usd":0.05,"structured_output":{"domain":"auth","clauses":["add rate limiting"]}}]'
tmp_feat=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tmp_feat"
run_hook "$tmp_feat" "sess-feat"
state_feat=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-feat.json")
assert_eq "calls_made incremented" "1" "$(echo "$state_feat" | jq -r '.calls_made')"
assert_eq "rendered_title set" "auth: add rate limiting" "$(echo "$state_feat" | jq -r '.rendered_title')"
last_line=$(tail -1 "$tmp_feat")
assert_eq "JSONL has custom-title" "custom-title" "$(echo "$last_line" | jq -r '.type')"

echo "-- LLM failure increments failure_count --"
export MOCK_CLAUDE_FAIL=1
tmp_f2=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tmp_f2"
run_hook "$tmp_f2" "sess-fail"
state_fail=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-fail.json")
assert_eq "failure_count is 1" "1" "$(echo "$state_fail" | jq -r '.failure_count // 0')"
unset MOCK_CLAUDE_FAIL

echo "-- Circuit breaker trips after 3 failures --"
export MOCK_CLAUDE_FAIL=1
tmp_cb=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tmp_cb"
# Pre-seed state with 2 failures to accelerate
mkdir -p "$CLAUDE_PLUGIN_DATA/state"
jq -nc '{version:"1.5", failure_count:2, llm_disabled:false, calls_made:0, overflow_used:0, accumulated_score:100, last_processed_turn:-1}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-cb.json"
run_hook "$tmp_cb" "sess-cb"
state_cb=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-cb.json")
assert_eq "failure_count is 3" "3" "$(echo "$state_cb" | jq -r '.failure_count')"
assert_eq "llm_disabled=true" "true" "$(echo "$state_cb" | jq -r '.llm_disabled')"
unset MOCK_CLAUDE_FAIL

echo "-- Idempotency: running hook twice on same turn does not double-count --"
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"duration_ms":200,"total_cost_usd":0.05,"structured_output":{"domain":"test","clauses":["a"]}}]'
tmp_idem=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tmp_idem"
run_hook "$tmp_idem" "sess-idem"
run_hook "$tmp_idem" "sess-idem"
state_idem=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-idem.json")
assert_eq "calls_made still 1" "1" "$(echo "$state_idem" | jq -r '.calls_made')"

echo "-- Manual /rename detection sets anchor --"
tmp_manual=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tmp_manual"
# Append a user-added custom-title (simulates /rename nativo)
jq -nc '{type:"custom-title", customTitle:"my-manual-title"}' >> "$tmp_manual"
run_hook "$tmp_manual" "sess-manual"
state_m=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-manual.json")
assert_eq "anchor set from manual rename" "my-manual-title" "$(echo "$state_m" | jq -r '.manual_anchor')"

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 4: Run integration tests**

```bash
bash tests/integration/test-end-to-end.sh
```
Expected: all pass.

- [ ] **Step 5: Run full test suite**

```bash
bash tests/run-tests.sh
```
Expected: 9 suites pass (8 unit + 1 integration).

- [ ] **Step 6: Commit**

```bash
git add tests/integration/ tests/fixtures/transcript-v15-qa.jsonl tests/fixtures/transcript-v15-pivot.jsonl
git commit -m "test(v1.5): add end-to-end integration tests with mocked claude"
```

---

### Task 7.2: Update plugin metadata and documentation

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update `.claude-plugin/plugin.json`**

Read the current file, then update the version field:
```bash
jq '.version = "1.5.0"' .claude-plugin/plugin.json > .claude-plugin/plugin.json.tmp && mv .claude-plugin/plugin.json.tmp .claude-plugin/plugin.json
```

- [ ] **Step 2: Replace `README.md` with v1.5 version**

The existing v1 README sections to replace and what each should now say:

1. **"How it works" section:** replace with the 8-step pipeline diagram from v1.5 spec §3.1. Mention work-score throttling and structured output explicitly.

2. **"Configuration" table:** replace table rows with the env vars from v1.5 spec §10.3 table (`SMART_RENAME_ENABLED`, `SMART_RENAME_MODEL`, `SMART_RENAME_BUDGET_CALLS`, `SMART_RENAME_OVERFLOW_SLOTS`, `SMART_RENAME_FIRST_THRESHOLD`, `SMART_RENAME_ONGOING_THRESHOLD`, `SMART_RENAME_REATTACH_INTERVAL`, `SMART_RENAME_CB_THRESHOLD`, `SMART_RENAME_LLM_TIMEOUT`, `SMART_RENAME_LOG_LEVEL`). For each env var, give the default value and one-line description.

3. **Add new "Cost model" section** placed between "How it works" and "Configuration":

   > Each LLM call in OAuth mode costs ~$0.10 because `claude -p` loads the full Claude Code context (~80k tokens of cache creation). The plugin budgets 6 calls per session (≈$0.60/session) with 2 manual overflow slots via `/smart-rename force`. Using `ANTHROPIC_API_KEY` with `--bare` would reduce cost by ~250× but that path is not the default (see v1.5 spec §1 for context).

4. **"FAQ" additions:**
   - "Why is there a budget?" → short answer referencing cost model
   - "How does the plugin decide when to rename?" → explain work-score heuristic briefly
   - "What if I want to control the name myself?" → explain `/smart-rename <name>` and `/smart-rename freeze`

5. **Remove the "update_interval" docs entirely** (no more fixed 3-message interval).

6. **Update "Subcommands" section** to list all 7 subcommands from v1.5 spec §7.2 with one-line descriptions.

7. **Update Quick Start** to show `/smart-rename explain` as the recommended command to verify the plugin is working.

- [ ] **Step 3: Update `CHANGELOG.md`**

Prepend:
```markdown
## 1.5.0 — 2026-04-14

### Changed (breaking)
- Complete rewrite as modular bash per responsibility
- Title format is now `domain: clause1, clause2, ...` (was kebab-case slug)
- Deterministic throttling replaces fixed 3-message interval
- Budget model: 6 LLM calls per session + 2 manual overflow slots
- State schema version bumped to 1.5; v1 states (if any existed in practice) are not migrated

### Added
- Structured output via `claude -p --json-schema` — no more fragile JSON parsing
- Subcommands: `/smart-rename <name>`, `freeze`, `unfreeze`, `force`, `explain`, `unanchor`
- Detection of `/rename` nativo as implicit anchor
- Circuit breaker after 3 consecutive LLM failures
- JSONL structured logs per session
- Idempotency via `last_processed_turn`
- Level 4 testing via Computer Use (planned)

### Removed
- Fixed 3-message interval
- Heuristic fallback when LLM fails (no more synthetic kebab-case from first prompt)
- v1 scripts: `generate-name.sh`, `session-writer.sh`, `utils.sh`
```

- [ ] **Step 4: Run shellcheck on all scripts**

```bash
shellcheck scripts/*.sh scripts/lib/*.sh tests/run-tests.sh tests/unit/*.sh tests/integration/*.sh || true
```
Fix any blocking issues. Advisory warnings may be left.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json README.md CHANGELOG.md
git commit -m "docs(v1.5): update README, CHANGELOG; bump plugin version to 1.5.0"
```

---

## Phase 8: Manual scenarios + Computer Use testing (Level 3 and 4)

### Task 8.1: Level 3 scenarios (LLM real, manual)

**Files:**
- Create: `docs/test-results/2026-04-14-level3-scenarios.md`

- [ ] **Step 1: Write scenarios**

Document 3 scenarios to execute manually in real Claude Code sessions:

1. **Scenario A — Short bugfix:** start a fresh session, paste a bug description involving 1-2 files. Run ~10 turns to completion. Record title evolution, calls_made, cost via `/smart-rename explain`.

2. **Scenario B — Long feature:** start a fresh session on a larger feature (e.g., adding OAuth2 flow). Run 30+ turns. Observe title evolution, budget consumption, behavior at budget exhaustion.

3. **Scenario C — Q&A exploration:** start a session asking conceptual questions with no tool calls. Confirm no LLM calls happen (pre-filter works).

For each, record:
- Turn count
- Actual calls_made and overflow_used at end
- Total cost (from log: `grep llm_call_end <session>.jsonl | jq -s 'map(.cost_usd) | add'`)
- Title quality assessment (subjective)
- Any unexpected behaviors

- [ ] **Step 2: Execute scenarios (human or agent)**

This step is a human activity or an agent-driven Computer Use session.

- [ ] **Step 3: Commit results**

```bash
git add docs/test-results/2026-04-14-level3-scenarios.md
git commit -m "test(v1.5): Level 3 manual scenario results"
```

---

### Task 8.2: Level 4 — Computer Use driven usability testing

**Files:**
- Create: `docs/test-results/2026-04-14-computer-use.md`

- [ ] **Step 1: Enable Computer Use**

In an interactive session, run `/mcp`, find `computer-use`, select Enable. Grant Accessibility and Screen Recording permissions in macOS Settings.

- [ ] **Step 2: Scenarios for Computer Use agent**

The agent executes these scenarios by driving a separate terminal via Computer Use:

1. **Skill smoke test:** new interactive session in a test project; invoke `/smart-rename freeze` and verify state JSON shows `frozen:true`; screenshot.

2. **Evolution:** open new session; send 10 coding prompts (e.g., "add a function foo", "now test foo", "refactor foo into bar"); observe state across turns; check `transition_history` contains 1-3 entries; screenshot session picker.

3. **Controls chain:** `freeze` → send 2 more turns → `/smart-rename explain` → `unfreeze` → `/smart-rename force` → `/smart-rename "my-feat"` → screenshot state at each step.

4. **`/rename` nativo detection:** use the native `/rename` command; run the hook one more time; verify `manual_anchor` updated.

5. **Circuit breaker:** set `claude -p` to fail (easy if API quota reached); verify state shows `llm_disabled: true` after 3 failures. Note: this may be hard to trigger artificially; optional scenario.

- [ ] **Step 3: Write report**

Document each scenario's outcome, screenshots, bugs found, calibration suggestions (e.g., "first_call_work_threshold of 20 feels too low for my patterns; 30 would be better").

- [ ] **Step 4: Commit report and any calibration changes**

```bash
git add docs/test-results/2026-04-14-computer-use.md
# If calibration changes needed:
#   edit config/default-config.json and commit separately as "tune(v1.5): adjust thresholds from Level 4 findings"
git commit -m "test(v1.5): Level 4 Computer Use usability report"
```

---

## Phase 9: Release

### Task 9.1: Tag and release v1.5.0

- [ ] **Step 1: Final review of all commits**

```bash
git log --oneline main..HEAD
```

- [ ] **Step 2: Ensure tests pass cleanly**

```bash
bash tests/run-tests.sh
shellcheck scripts/*.sh scripts/lib/*.sh
```

- [ ] **Step 3: Tag release**

```bash
git tag -a v1.5.0 -m "Smart Session Rename v1.5.0 — greenfield, structured output, work-score throttling"
```

- [ ] **Step 4: Decide on publication**

Push tag to GitHub if you maintain a public plugin:
```bash
git push origin main
git push origin v1.5.0
```

Otherwise keep local.

---

## Self-Review (spec coverage check)

Spec sections covered by tasks:

- **§1 Contexto/motivação** — not code; captured in README + CHANGELOG (Task 7.2)
- **§2 Requisitos** — behavior captured across tasks: throttling (Task 3.2), subcommands (Task 6.1), title format (Task 4.3), budget (Task 3.2), /rename detection (Task 5.1)
- **§3 Arquitetura** — Phase 2-5 implement each module
- **§3.5 Schema transcript** — Task 3.1 parser emits it
- **§4 Throttling** — Task 3.2 scorer
- **§5 LLM** — Task 4.2 llm.sh + Task 4.1 prompt + Task 4.3 validate
- **§6 State** — Task 1.3 state.sh; state schema enforced implicitly by hook (Task 5.1)
- **§7 Skill** — Task 2.1 prototype + Task 6.1 full
- **§8 Erros** — Task 5.1 error handling matrix + Task 3.2 circuit breaker
- **§9 Logs** — Task 1.2 logger.sh + used throughout
- **§10 Config** — Task 1.1 config.sh
- **§11 Testes** — Unit in Phase 1-4; integration in Task 7.1; Level 3 in Task 8.1; Level 4 in Task 8.2
- **§12 Riscos** — mitigations embedded (circuit breaker, idempotency, stale lock, etc.)
- **§13 Rollout** — this plan IS the rollout (Phases 1-9)
- **§14 DoD** — mirrored in Phase 9

Gaps: none known. Any discovered during implementation → add a follow-up task.
