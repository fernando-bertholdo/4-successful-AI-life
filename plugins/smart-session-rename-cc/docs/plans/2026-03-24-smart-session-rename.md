# Smart Session Rename — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin that automatically names and evolves session titles based on conversation content.

**Architecture:** A `Stop` hook (async) fires after each Claude response, runs a bash script that counts messages, decides whether to name/rename, generates a name via `claude -p`, and writes the title to the session JSONL file. A companion skill `/smart-rename` provides on-demand renaming.

**Tech Stack:** Bash scripts, `jq` for JSON parsing, `claude -p` for name generation, `flock` for concurrency.

**Spec:** `docs/specs/2026-03-24-smart-session-rename-design.md`

---

## File Structure

```
smart-session-rename/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── hooks/
│   └── hooks.json               # Stop hook config
├── scripts/
│   ├── rename-hook.sh           # Main hook entry point — orchestrates the flow
│   ├── generate-name.sh         # Calls claude -p to generate/update names
│   ├── session-writer.sh        # Writes customTitle to session JSONL
│   └── utils.sh                 # Config loading, JSON helpers, logging
├── skills/
│   └── smart-rename/
│       └── SKILL.md             # On-demand /smart-rename skill
├── config/
│   └── default-config.json      # Default configuration values
├── tests/
│   ├── test-utils.sh            # Tests for utils.sh
│   ├── test-generate-name.sh    # Tests for name generation + parsing
│   ├── test-rename-hook.sh      # Integration tests for the hook flow
│   ├── test-session-writer.sh   # Tests for session file writing
│   ├── run-tests.sh             # Test runner
│   └── fixtures/
│       ├── hook-input-basic.json
│       ├── hook-input-short-prompt.json
│       ├── transcript-basic.jsonl
│       ├── transcript-short.jsonl
│       └── transcript-multi-turn.jsonl
├── README.md
├── LICENSE
└── CHANGELOG.md
```

**Responsibilities per file:**

| File | Single Responsibility |
|---|---|
| `utils.sh` | Load config (env > file > defaults), log to file, parse JSON via jq, validate name format |
| `generate-name.sh` | Build prompt from transcript context, call `claude -p`, parse and validate output |
| `session-writer.sh` | Resolve session file path, append customTitle record, handle errors |
| `rename-hook.sh` | Orchestrate: read stdin → load state → count messages → decide → call generate → call writer → save state |

---

## Task 0: Repository Bootstrap

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `hooks/hooks.json`
- Create: `config/default-config.json`
- Create: `LICENSE`
- Create: `CHANGELOG.md`

- [ ] **Step 1: Initialize git repo**

```bash
cd /sessions/sharp-gifted-tesla/mnt/smart-session-rename
git init
```

- [ ] **Step 2: Create plugin manifest**

Create `.claude-plugin/plugin.json`:
```json
{
  "name": "smart-session-rename",
  "version": "1.0.0",
  "description": "Automatically names and renames Claude Code sessions based on conversation content",
  "author": {
    "name": "Fernando Bertholdo",
    "url": "https://github.com/fe-bertholdo"
  },
  "repository": "https://github.com/fe-bertholdo/smart-session-rename",
  "license": "MIT",
  "keywords": ["session", "rename", "productivity", "hooks", "auto-name"],
  "hooks": "./hooks/hooks.json",
  "skills": "./skills/"
}
```

- [ ] **Step 3: Create hook configuration**

Create `hooks/hooks.json`:
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/rename-hook.sh",
            "timeout": 30,
            "async": true
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 4: Create default config**

Create `config/default-config.json`:
```json
{
  "enabled": true,
  "update_interval": 3,
  "min_first_prompt_words": 10,
  "max_title_words": 5
}
```

- [ ] **Step 5: Create LICENSE (MIT) and CHANGELOG.md**

MIT license with Fernando Bertholdo's name. CHANGELOG with initial `## [1.0.0] - 2026-03-24` section.

- [ ] **Step 6: Create .gitignore**

```
*.log
.DS_Store
tmp/
```

- [ ] **Step 7: Commit**

```bash
git add .claude-plugin/ hooks/ config/ LICENSE CHANGELOG.md .gitignore
git commit -m "chore: bootstrap plugin structure with manifest, hooks, and config"
```

---

## Task 1: Utility Functions (`scripts/utils.sh`)

**Files:**
- Create: `scripts/utils.sh`
- Create: `tests/test-utils.sh`
- Create: `tests/run-tests.sh`

- [ ] **Step 1: Write tests for config loading**

Create `tests/test-utils.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../scripts/utils.sh"

PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "  ✓ $desc"
    ((PASS++))
  else
    echo "  ✗ $desc: expected '$expected', got '$actual'"
    ((FAIL++))
  fi
}

echo "=== utils.sh tests ==="

# Test: defaults when no env or config file
echo "-- config loading --"
unset SMART_RENAME_ENABLED SMART_RENAME_UPDATE_INTERVAL SMART_RENAME_MIN_WORDS SMART_RENAME_MAX_TITLE_WORDS 2>/dev/null || true
CLAUDE_PLUGIN_DATA="$(mktemp -d)"
load_config
assert_eq "default enabled" "true" "$CFG_ENABLED"
assert_eq "default update_interval" "3" "$CFG_UPDATE_INTERVAL"
assert_eq "default min_words" "10" "$CFG_MIN_FIRST_PROMPT_WORDS"
assert_eq "default max_title_words" "5" "$CFG_MAX_TITLE_WORDS"

# Test: env vars override defaults
export SMART_RENAME_UPDATE_INTERVAL=7
export SMART_RENAME_ENABLED=false
load_config
assert_eq "env overrides enabled" "false" "$CFG_ENABLED"
assert_eq "env overrides interval" "7" "$CFG_UPDATE_INTERVAL"
unset SMART_RENAME_UPDATE_INTERVAL SMART_RENAME_ENABLED

# Test: config file overrides defaults
mkdir -p "$CLAUDE_PLUGIN_DATA"
echo '{"update_interval":5,"max_title_words":3}' > "$CLAUDE_PLUGIN_DATA/config.json"
load_config
assert_eq "config file overrides interval" "5" "$CFG_UPDATE_INTERVAL"
assert_eq "config file overrides max_words" "3" "$CFG_MAX_TITLE_WORDS"
assert_eq "config file keeps default enabled" "true" "$CFG_ENABLED"

# Test: env vars override config file
export SMART_RENAME_UPDATE_INTERVAL=9
load_config
assert_eq "env beats config file" "9" "$CFG_UPDATE_INTERVAL"
unset SMART_RENAME_UPDATE_INTERVAL

# Test: validate_name
echo "-- name validation --"
assert_eq "valid kebab" "0" "$(validate_name "fix-login-bug"; echo $?)"
assert_eq "valid single word" "0" "$(validate_name "refactor"; echo $?)"
assert_eq "reject spaces" "1" "$(validate_name "fix login bug"; echo $?)"
assert_eq "reject empty" "1" "$(validate_name ""; echo $?)"
assert_eq "reject too many words" "1" "$(validate_name "a-b-c-d-e-f-g"; echo $?)"

# Test: count_words
echo "-- word counting --"
assert_eq "count simple" "4" "$(count_words "hello world foo bar")"
assert_eq "count single" "1" "$(count_words "hello")"
assert_eq "count empty" "0" "$(count_words "")"

# Cleanup
rm -rf "$CLAUDE_PLUGIN_DATA"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
```

- [ ] **Step 2: Create test runner**

Create `tests/run-tests.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOTAL_PASS=0
TOTAL_FAIL=0

for test_file in "$SCRIPT_DIR"/test-*.sh; do
  echo ""
  echo "Running $(basename "$test_file")..."
  if bash "$test_file"; then
    ((TOTAL_PASS++))
  else
    ((TOTAL_FAIL++))
  fi
done

echo ""
echo "=============================="
echo "Test suites: $TOTAL_PASS passed, $TOTAL_FAIL failed"
[[ $TOTAL_FAIL -eq 0 ]] && exit 0 || exit 1
```

- [ ] **Step 3: Run tests — expect FAIL (source file missing)**

```bash
bash tests/test-utils.sh
```
Expected: FAIL — `scripts/utils.sh: No such file or directory`

- [ ] **Step 4: Implement utils.sh**

Create `scripts/utils.sh`:
```bash
#!/usr/bin/env bash
# utils.sh — Configuration loading, name validation, logging, JSON helpers
# Sourced by other scripts, never run directly.

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_CONFIG="$PLUGIN_DIR/config/default-config.json"

# --- Config Loading ---
# Precedence: env vars > config file > defaults
load_config() {
  # Load defaults
  CFG_ENABLED="true"
  CFG_UPDATE_INTERVAL="3"
  CFG_MIN_FIRST_PROMPT_WORDS="10"
  CFG_MAX_TITLE_WORDS="5"

  # Override from config file if exists
  local config_file="${CLAUDE_PLUGIN_DATA:-}/config.json"
  if [[ -f "$config_file" ]]; then
    CFG_ENABLED=$(jq -r '.enabled // empty' "$config_file" 2>/dev/null || echo "")
    [[ -z "$CFG_ENABLED" ]] && CFG_ENABLED="true"

    local val
    val=$(jq -r '.update_interval // empty' "$config_file" 2>/dev/null || echo "")
    [[ -n "$val" ]] && CFG_UPDATE_INTERVAL="$val"

    val=$(jq -r '.min_first_prompt_words // empty' "$config_file" 2>/dev/null || echo "")
    [[ -n "$val" ]] && CFG_MIN_FIRST_PROMPT_WORDS="$val"

    val=$(jq -r '.max_title_words // empty' "$config_file" 2>/dev/null || echo "")
    [[ -n "$val" ]] && CFG_MAX_TITLE_WORDS="$val"
  fi

  # Override from env vars (highest priority)
  [[ -n "${SMART_RENAME_ENABLED:-}" ]] && CFG_ENABLED="$SMART_RENAME_ENABLED"
  [[ -n "${SMART_RENAME_UPDATE_INTERVAL:-}" ]] && CFG_UPDATE_INTERVAL="$SMART_RENAME_UPDATE_INTERVAL"
  [[ -n "${SMART_RENAME_MIN_WORDS:-}" ]] && CFG_MIN_FIRST_PROMPT_WORDS="$SMART_RENAME_MIN_WORDS"
  [[ -n "${SMART_RENAME_MAX_TITLE_WORDS:-}" ]] && CFG_MAX_TITLE_WORDS="$SMART_RENAME_MAX_TITLE_WORDS"
}

# --- Name Validation ---
# Returns 0 if valid, 1 if invalid
validate_name() {
  local name="$1"
  # Reject empty
  [[ -z "$name" ]] && return 1
  # Reject if contains spaces
  [[ "$name" =~ \  ]] && return 1
  # Reject if more than 6 hyphen-separated words
  local word_count
  word_count=$(echo "$name" | tr '-' '\n' | wc -l)
  [[ "$word_count" -gt 6 ]] && return 1
  return 0
}

# --- Word Counting ---
count_words() {
  local text="$1"
  [[ -z "$text" ]] && echo "0" && return
  echo "$text" | wc -w | tr -d ' '
}

# --- Logging ---
log_info() {
  local session_id="${1:-unknown}"
  local message="$2"
  local log_dir="${CLAUDE_PLUGIN_DATA:-/tmp}/logs"
  mkdir -p "$log_dir"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] INFO: $message" >> "$log_dir/$session_id.log"
}

log_error() {
  local session_id="${1:-unknown}"
  local message="$2"
  local log_dir="${CLAUDE_PLUGIN_DATA:-/tmp}/logs"
  mkdir -p "$log_dir"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: $message" >> "$log_dir/$session_id.log"
}

# --- State Management ---
# Atomic write: write to temp file, then rename
write_state() {
  local state_file="$1"
  local content="$2"
  local state_dir
  state_dir="$(dirname "$state_file")"
  mkdir -p "$state_dir"
  local tmp_file
  tmp_file=$(mktemp "$state_dir/.tmp.XXXXXX")
  echo "$content" > "$tmp_file"
  mv "$tmp_file" "$state_file"
}

read_state() {
  local state_file="$1"
  if [[ -f "$state_file" ]]; then
    cat "$state_file"
  else
    echo '{}'
  fi
}
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
bash tests/test-utils.sh
```
Expected: All assertions pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/utils.sh tests/test-utils.sh tests/run-tests.sh
git commit -m "feat: add utils.sh with config loading, name validation, and logging"
```

---

## Task 2: Name Generation (`scripts/generate-name.sh`)

**Files:**
- Create: `scripts/generate-name.sh`
- Create: `tests/test-generate-name.sh`
- Create: `tests/fixtures/transcript-basic.jsonl`
- Create: `tests/fixtures/transcript-short.jsonl`
- Create: `tests/fixtures/transcript-multi-turn.jsonl`

- [ ] **Step 1: Create test fixtures**

Create `tests/fixtures/transcript-basic.jsonl` — a realistic session JSONL with one user turn (>10 words) and one assistant turn:
```jsonl
{"role":"user","type":"human","content":"I need to refactor the authentication middleware to support OAuth2 tokens instead of session cookies"}
{"role":"assistant","type":"text","content":"I'll help you refactor the authentication middleware..."}
```

Create `tests/fixtures/transcript-short.jsonl` — a session with a short first prompt (<10 words):
```jsonl
{"role":"user","type":"human","content":"hi there"}
{"role":"assistant","type":"text","content":"Hello! How can I help?"}
```

Create `tests/fixtures/transcript-multi-turn.jsonl` — a session with 5 user turns showing evolving work:
```jsonl
{"role":"user","type":"human","content":"I need to refactor the authentication middleware to support OAuth2 tokens"}
{"role":"assistant","type":"text","content":"I'll help with that..."}
{"role":"user","type":"human","content":"Also add rate limiting to the auth endpoints"}
{"role":"assistant","type":"text","content":"Good idea, I'll add rate limiting..."}
{"role":"user","type":"human","content":"Now let's write tests for the new auth flow"}
{"role":"assistant","type":"text","content":"Let me write comprehensive tests..."}
{"role":"user","type":"human","content":"Can you also update the API documentation for these changes?"}
{"role":"assistant","type":"text","content":"I'll update the docs..."}
{"role":"user","type":"human","content":"Perfect, let's also add integration tests with the database"}
{"role":"assistant","type":"text","content":"Adding integration tests..."}
```

- [ ] **Step 2: Write tests for name generation functions**

Create `tests/test-generate-name.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../scripts/utils.sh"
source "$SCRIPT_DIR/../scripts/generate-name.sh"

PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "  ✓ $desc"
    ((PASS++))
  else
    echo "  ✗ $desc: expected '$expected', got '$actual'"
    ((FAIL++))
  fi
}

echo "=== generate-name.sh tests ==="

# Test: extract_first_user_prompt
echo "-- extract_first_user_prompt --"
result=$(extract_first_user_prompt "$SCRIPT_DIR/fixtures/transcript-basic.jsonl")
assert_eq "extracts first prompt" "I need to refactor the authentication middleware to support OAuth2 tokens instead of session cookies" "$result"

result=$(extract_first_user_prompt "$SCRIPT_DIR/fixtures/transcript-short.jsonl")
assert_eq "extracts short prompt" "hi there" "$result"

# Test: extract_recent_context
echo "-- extract_recent_context --"
result=$(extract_recent_context "$SCRIPT_DIR/fixtures/transcript-multi-turn.jsonl" 2)
# Should contain the last 2 user messages
echo "$result" | grep -q "integration tests" && { echo "  ✓ recent context has last message"; ((PASS++)); } || { echo "  ✗ recent context missing last message"; ((FAIL++)); }
echo "$result" | grep -q "API documentation" && { echo "  ✓ recent context has second-to-last"; ((PASS++)); } || { echo "  ✗ recent context missing second-to-last"; ((FAIL++)); }

# Test: count_user_messages
echo "-- count_user_messages --"
result=$(count_user_messages "$SCRIPT_DIR/fixtures/transcript-basic.jsonl")
assert_eq "basic has 1 user msg" "1" "$result"

result=$(count_user_messages "$SCRIPT_DIR/fixtures/transcript-multi-turn.jsonl")
assert_eq "multi-turn has 5 user msgs" "5" "$result"

# Test: parse_generated_name (validates and cleans LLM output)
echo "-- parse_generated_name --"
assert_eq "clean kebab" "fix-auth-middleware" "$(parse_generated_name "fix-auth-middleware")"
assert_eq "strips whitespace" "fix-auth" "$(parse_generated_name "  fix-auth  ")"
assert_eq "strips newlines" "refactor-login" "$(parse_generated_name $'refactor-login\n')"
assert_eq "reject spaces returns empty" "" "$(parse_generated_name "fix auth bug")"
assert_eq "reject empty" "" "$(parse_generated_name "")"
assert_eq "reject too long" "" "$(parse_generated_name "a-b-c-d-e-f-g")"

# Test: fallback_name (heuristic from first prompt)
echo "-- fallback_name --"
result=$(fallback_name "I need to refactor the authentication middleware")
# Should be kebab-case, max 4 words
echo "$result" | grep -qE '^[a-z0-9-]+$' && { echo "  ✓ fallback is kebab-case"; ((PASS++)); } || { echo "  ✗ fallback not kebab-case: $result"; ((FAIL++)); }
word_count=$(echo "$result" | tr '-' '\n' | wc -l)
[[ "$word_count" -le 4 ]] && { echo "  ✓ fallback max 4 words"; ((PASS++)); } || { echo "  ✗ fallback too long: $result ($word_count words)"; ((FAIL++)); }

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
bash tests/test-generate-name.sh
```
Expected: FAIL — source file missing

- [ ] **Step 4: Implement generate-name.sh**

Create `scripts/generate-name.sh`:
```bash
#!/usr/bin/env bash
# generate-name.sh — Name generation via claude -p and fallback heuristics
# Sourced by rename-hook.sh. Requires utils.sh to be sourced first.

# Extract the first user message from a transcript JSONL
extract_first_user_prompt() {
  local transcript="$1"
  jq -r 'select(.role == "user" and .type == "human") | .content' "$transcript" | head -1
}

# Extract recent user messages (last N) from transcript
extract_recent_context() {
  local transcript="$1"
  local count="${2:-2}"
  jq -r 'select(.role == "user" and .type == "human") | .content' "$transcript" | tail -"$count"
}

# Count user messages in transcript
count_user_messages() {
  local transcript="$1"
  jq -r 'select(.role == "user" and .type == "human") | .content' "$transcript" | wc -l | tr -d ' '
}

# Validate and clean LLM output into a valid session name
parse_generated_name() {
  local raw="$1"
  # Strip whitespace and newlines
  local cleaned
  cleaned=$(echo "$raw" | tr -d '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  # Strip surrounding quotes if present
  cleaned=$(echo "$cleaned" | sed "s/^['\"]//;s/['\"]$//")
  # Validate
  if validate_name "$cleaned"; then
    echo "$cleaned"
  else
    echo ""
  fi
}

# Fallback: generate a name heuristically from the first prompt
# Takes the first 4 meaningful words, lowercases, joins with hyphens
fallback_name() {
  local prompt="$1"
  echo "$prompt" \
    | tr '[:upper:]' '[:lower:]' \
    | tr -cs 'a-z0-9 ' ' ' \
    | awk '{for(i=1;i<=NF && i<=4;i++) printf "%s%s",$i,(i<4 && i<NF?"-":""); print ""}' \
    | sed 's/-$//'
}

# Generate initial session name using claude -p
generate_initial_name() {
  local first_prompt="$1"
  local cwd="$2"

  local prompt
  prompt="You are naming a Claude Code session. Based on the user's first message, generate a concise 2-4 word kebab-case session name that captures the primary intent.

User's first message:
\"\"\"
${first_prompt}
\"\"\"

Working directory: ${cwd}

Rules:
- Use kebab-case (e.g., fix-login-bug, refactor-auth-module)
- 2-4 words maximum
- Focus on the ACTION and TARGET (what + where)
- Output ONLY the name, nothing else
- No quotes, no explanation, no newlines
- Example valid output: fix-login-validation"

  local raw_name
  raw_name=$(claude -p "$prompt" 2>/dev/null) || raw_name=""

  local name
  name=$(parse_generated_name "$raw_name")

  if [[ -n "$name" ]]; then
    echo "$name"
  else
    fallback_name "$first_prompt"
  fi
}

# Generate updated session name using claude -p
generate_updated_name() {
  local current_title="$1"
  local original_title="$2"
  local recent_context="$3"

  local prompt
  prompt="You are updating a Claude Code session name. The session has evolved. Derive a new name from the current one that reflects the broader scope.

Current title: ${current_title}
Original title: ${original_title}

Recent conversation context (last 2-3 turns):
\"\"\"
${recent_context}
\"\"\"

Rules:
- Evolve from the current title, don't create something unrelated
- Use kebab-case, 2-5 words maximum
- If the work hasn't meaningfully changed scope, output the current title unchanged
- Output ONLY the name, nothing else
- No quotes, no explanation, no newlines"

  local raw_name
  raw_name=$(claude -p "$prompt" 2>/dev/null) || raw_name=""

  local name
  name=$(parse_generated_name "$raw_name")

  if [[ -n "$name" ]]; then
    echo "$name"
  else
    # If LLM fails, keep current title
    echo "$current_title"
  fi
}
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
bash tests/test-generate-name.sh
```
Expected: All unit tests pass. (The `generate_initial_name` and `generate_updated_name` functions call `claude -p` and are tested via integration tests in Task 4.)

- [ ] **Step 6: Commit**

```bash
git add scripts/generate-name.sh tests/test-generate-name.sh tests/fixtures/
git commit -m "feat: add name generation with LLM prompts, parsing, and fallback heuristics"
```

---

## Task 3: Reverse-Engineer Session JSONL Format

**Files:**
- Create: `docs/session-format-research.md`

> **CRITICAL:** This task MUST be completed before implementing the session writer. The session file format is undocumented and our `write_session_title()` depends on it being correct.

- [ ] **Step 1: Find a real session file**

```bash
# List session files, look for one that has been renamed with /rename
find ~/.claude/projects -name "*.jsonl" -type f 2>/dev/null | head -20
```

- [ ] **Step 2: Inspect a session file that was renamed via /rename**

```bash
# Pick one of the files found above and look for title/rename entries
# Look for entries with "customTitle", "title", "rename", or "sessionTitle"
cat <session-file>.jsonl | jq -c 'select(.type? // "" | test("title|rename|summary"; "i")) // select(.customTitle? != null)' 2>/dev/null | head -5
```

If no renamed sessions exist, create one:
```bash
claude --name "test-format-research"
# In the session: /rename format-test-session
# Then exit and inspect the JSONL
```

- [ ] **Step 3: Document the exact format**

Create `docs/session-format-research.md` with:
- The exact JSON structure of a title/rename record
- Which fields are required vs optional
- Where in the file the record appears (appended? inserted?)
- Any other metadata entries relevant to session identity

- [ ] **Step 4: Update session-writer.sh implementation accordingly**

If the format differs from our initial guess (`{"type":"sessionTitle",...}`), update the Task 4 implementation to match. Document the format in a code comment.

- [ ] **Step 5: Commit**

```bash
git add docs/session-format-research.md
git commit -m "research: document session JSONL title record format"
```

---

## Task 4: Session File Writer (`scripts/session-writer.sh`)

**Files:**
- Create: `scripts/session-writer.sh`
- Create: `tests/test-session-writer.sh`

- [ ] **Step 1: Write tests for session writing**

Create `tests/test-session-writer.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../scripts/utils.sh"
source "$SCRIPT_DIR/../scripts/session-writer.sh"

PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "  ✓ $desc"
    ((PASS++))
  else
    echo "  ✗ $desc: expected '$expected', got '$actual'"
    ((FAIL++))
  fi
}

echo "=== session-writer.sh tests ==="

# Setup: create a fake session file
TMPDIR_TEST=$(mktemp -d)
FAKE_SESSION="$TMPDIR_TEST/test-session.jsonl"
echo '{"role":"user","type":"human","content":"test"}' > "$FAKE_SESSION"

# Test: write_session_title appends to file
echo "-- write_session_title --"
write_session_title "$FAKE_SESSION" "fix-auth-bug" "test-session-id"
last_line=$(tail -1 "$FAKE_SESSION")
echo "$last_line" | jq -e '.type == "sessionTitle"' > /dev/null 2>&1 \
  && { echo "  ✓ appends sessionTitle record"; ((PASS++)); } \
  || { echo "  ✗ missing sessionTitle type: $last_line"; ((FAIL++)); }

echo "$last_line" | jq -e '.title == "fix-auth-bug"' > /dev/null 2>&1 \
  && { echo "  ✓ title field correct"; ((PASS++)); } \
  || { echo "  ✗ wrong title: $last_line"; ((FAIL++)); }

# Test: writing to non-existent file logs error and returns 1
echo "-- error handling --"
export CLAUDE_PLUGIN_DATA="$TMPDIR_TEST/plugin-data"
write_session_title "/nonexistent/path/session.jsonl" "test-name" "bad-session" 2>/dev/null
result=$?
assert_eq "returns 1 on bad path" "1" "$result"

# Verify error was logged
if [[ -f "$CLAUDE_PLUGIN_DATA/logs/bad-session.log" ]]; then
  echo "  ✓ error logged to file"
  ((PASS++))
else
  echo "  ✗ no error log created"
  ((FAIL++))
fi

# Cleanup
rm -rf "$TMPDIR_TEST"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
bash tests/test-session-writer.sh
```
Expected: FAIL — source file missing

- [ ] **Step 3: Implement session-writer.sh**

Create `scripts/session-writer.sh`:
```bash
#!/usr/bin/env bash
# session-writer.sh — Writes session title to JSONL session files
# Sourced by rename-hook.sh. Requires utils.sh to be sourced first.

# Write a customTitle record to the session JSONL file.
# Uses the transcript_path directly from hook input.
#
# Args:
#   $1 - session_file: path to the session JSONL file
#   $2 - title: the session name to write
#   $3 - session_id: for logging purposes
#
# Returns: 0 on success, 1 on failure
write_session_title() {
  local session_file="$1"
  local title="$2"
  local session_id="$3"

  # Verify file exists and is writable
  if [[ ! -f "$session_file" ]]; then
    log_error "$session_id" "Session file not found: $session_file"
    return 1
  fi

  if [[ ! -w "$session_file" ]]; then
    log_error "$session_id" "Session file not writable: $session_file"
    return 1
  fi

  # Build the title record
  local timestamp
  timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  local record
  record=$(jq -cn \
    --arg type "sessionTitle" \
    --arg title "$title" \
    --arg ts "$timestamp" \
    '{type: $type, title: $title, timestamp: $ts}')

  # Append to session file
  if echo "$record" >> "$session_file"; then
    log_info "$session_id" "Title written: '$title' -> $session_file"
    return 0
  else
    log_error "$session_id" "Failed to write title to: $session_file"
    return 1
  fi
}
```

> **IMPORTANT NOTE:** The `type: "sessionTitle"` record format is a best-guess based on research. During actual implementation, the first step MUST be to inspect a real session file where `/rename` was used, to verify the exact format. Adjust the `record` construction accordingly. This is called out in the spec as "Implementation step 0."

- [ ] **Step 4: Run tests — expect PASS**

```bash
bash tests/test-session-writer.sh
```
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/session-writer.sh tests/test-session-writer.sh
git commit -m "feat: add session-writer with title appending and error logging"
```

---

## Task 5: Main Hook Script (`scripts/rename-hook.sh`)

**Files:**
- Create: `scripts/rename-hook.sh`
- Create: `tests/test-rename-hook.sh`
- Create: `tests/fixtures/hook-input-basic.json`
- Create: `tests/fixtures/hook-input-short-prompt.json`

- [ ] **Step 1: Create test fixtures for hook input**

Create `tests/fixtures/hook-input-basic.json`:
```json
{
  "session_id": "test-session-001",
  "transcript_path": "",
  "cwd": "/home/user/my-project",
  "hook_event_name": "Stop"
}
```
(The `transcript_path` will be dynamically set in tests to point at fixtures.)

- [ ] **Step 2: Write integration tests**

Create `tests/test-rename-hook.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "  ✓ $desc"
    ((PASS++))
  else
    echo "  ✗ $desc: expected '$expected', got '$actual'"
    ((FAIL++))
  fi
}

echo "=== rename-hook.sh integration tests ==="

# Setup
TMPDIR_TEST=$(mktemp -d)
export CLAUDE_PLUGIN_DATA="$TMPDIR_TEST/plugin-data"
mkdir -p "$CLAUDE_PLUGIN_DATA/state"

# We need to mock claude -p since it won't be available in tests
# Create a mock that returns a predictable name
MOCK_BIN="$TMPDIR_TEST/bin"
mkdir -p "$MOCK_BIN"
cat > "$MOCK_BIN/claude" << 'MOCK'
#!/usr/bin/env bash
# Mock claude CLI — returns a fixed name
echo "refactor-auth-middleware"
MOCK
chmod +x "$MOCK_BIN/claude"
export PATH="$MOCK_BIN:$PATH"

# Create a writable copy of transcript fixture
TRANSCRIPT="$TMPDIR_TEST/session.jsonl"
cp "$SCRIPT_DIR/fixtures/transcript-basic.jsonl" "$TRANSCRIPT"

# Test 1: First run should generate initial title
echo "-- first run: initial naming --"
HOOK_INPUT=$(jq -n \
  --arg sid "test-001" \
  --arg tp "$TRANSCRIPT" \
  --arg cwd "/home/user/project" \
  '{session_id: $sid, transcript_path: $tp, cwd: $cwd, hook_event_name: "Stop"}')

echo "$HOOK_INPUT" | bash "$SCRIPT_DIR/../scripts/rename-hook.sh"

# Check state was created
STATE_FILE="$CLAUDE_PLUGIN_DATA/state/test-001.json"
if [[ -f "$STATE_FILE" ]]; then
  echo "  ✓ state file created"
  ((PASS++))

  current_title=$(jq -r '.current_title' "$STATE_FILE")
  assert_eq "title was set" "refactor-auth-middleware" "$current_title"

  original_title=$(jq -r '.original_title' "$STATE_FILE")
  assert_eq "original_title matches" "refactor-auth-middleware" "$original_title"

  msg_count=$(jq -r '.message_count' "$STATE_FILE")
  assert_eq "message count recorded" "1" "$msg_count"
else
  echo "  ✗ state file not created"
  ((FAIL++))
fi

# Check title was written to session file
last_line=$(tail -1 "$TRANSCRIPT")
echo "$last_line" | jq -e '.title == "refactor-auth-middleware"' > /dev/null 2>&1 \
  && { echo "  ✓ title written to session file"; ((PASS++)); } \
  || { echo "  ✗ title not in session file"; ((FAIL++)); }

# Test 2: Short prompt should NOT trigger naming
echo "-- short prompt: skip naming --"
TRANSCRIPT_SHORT="$TMPDIR_TEST/session-short.jsonl"
cp "$SCRIPT_DIR/fixtures/transcript-short.jsonl" "$TRANSCRIPT_SHORT"

HOOK_INPUT_SHORT=$(jq -n \
  --arg sid "test-002" \
  --arg tp "$TRANSCRIPT_SHORT" \
  --arg cwd "/home/user/project" \
  '{session_id: $sid, transcript_path: $tp, cwd: $cwd, hook_event_name: "Stop"}')

echo "$HOOK_INPUT_SHORT" | bash "$SCRIPT_DIR/../scripts/rename-hook.sh"

STATE_SHORT="$CLAUDE_PLUGIN_DATA/state/test-002.json"
if [[ -f "$STATE_SHORT" ]]; then
  current_title=$(jq -r '.current_title // "none"' "$STATE_SHORT")
  assert_eq "no title for short prompt" "none" "$current_title"
else
  echo "  ✓ no state for short prompt (skipped entirely)"
  ((PASS++))
fi

# Test 3: Disabled via config should skip
echo "-- disabled: skip --"
export SMART_RENAME_ENABLED=false
HOOK_INPUT_DISABLED=$(jq -n \
  --arg sid "test-003" \
  --arg tp "$TRANSCRIPT" \
  --arg cwd "/home/user/project" \
  '{session_id: $sid, transcript_path: $tp, cwd: $cwd, hook_event_name: "Stop"}')

echo "$HOOK_INPUT_DISABLED" | bash "$SCRIPT_DIR/../scripts/rename-hook.sh"

STATE_DISABLED="$CLAUDE_PLUGIN_DATA/state/test-003.json"
[[ ! -f "$STATE_DISABLED" ]] \
  && { echo "  ✓ skipped when disabled"; ((PASS++)); } \
  || { echo "  ✗ should have skipped"; ((FAIL++)); }
unset SMART_RENAME_ENABLED

# Test 4: Missing transcript_path should attempt fallback
echo "-- fallback path resolution --"
HOOK_INPUT_NOPATH=$(jq -n \
  --arg sid "test-004" \
  --arg cwd "/home/user/project" \
  '{session_id: $sid, transcript_path: "", cwd: $cwd, hook_event_name: "Stop"}')

echo "$HOOK_INPUT_NOPATH" | bash "$SCRIPT_DIR/../scripts/rename-hook.sh" 2>/dev/null
# Should exit gracefully (no crash), state may or may not be created
echo "  ✓ handles missing transcript_path without crash"
((PASS++))

# Test 5: Corrupted state file should not crash
echo "-- corrupted state --"
mkdir -p "$CLAUDE_PLUGIN_DATA/state"
echo "NOT VALID JSON" > "$CLAUDE_PLUGIN_DATA/state/test-005.json"
HOOK_INPUT_CORRUPT=$(jq -n \
  --arg sid "test-005" \
  --arg tp "$TRANSCRIPT" \
  --arg cwd "/home/user/project" \
  '{session_id: $sid, transcript_path: $tp, cwd: $cwd, hook_event_name: "Stop"}')

echo "$HOOK_INPUT_CORRUPT" | bash "$SCRIPT_DIR/../scripts/rename-hook.sh" 2>/dev/null
echo "  ✓ handles corrupted state without crash"
((PASS++))

# Cleanup
rm -rf "$TMPDIR_TEST"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
bash tests/test-rename-hook.sh
```
Expected: FAIL — `rename-hook.sh` doesn't exist yet

- [ ] **Step 4: Implement rename-hook.sh**

Create `scripts/rename-hook.sh`:
```bash
#!/usr/bin/env bash
# rename-hook.sh — Main hook entry point for smart session renaming.
# Called by Claude Code's Stop hook. Reads JSON from stdin.
#
# Flow:
# 1. Read hook input (session_id, transcript_path, cwd)
# 2. Load config and state
# 3. Count user messages
# 4. Decide: initial name, update, or skip
# 5. Generate name (LLM or fallback)
# 6. Write to session file
# 7. Save state
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
source "$SCRIPT_DIR/generate-name.sh"
source "$SCRIPT_DIR/session-writer.sh"

# --- Read hook input from stdin ---
HOOK_INPUT=$(cat)
SESSION_ID=$(echo "$HOOK_INPUT" | jq -r '.session_id // empty')
TRANSCRIPT_PATH=$(echo "$HOOK_INPUT" | jq -r '.transcript_path // empty')
CWD=$(echo "$HOOK_INPUT" | jq -r '.cwd // empty')

# Check required dependencies
for cmd in jq claude; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "smart-session-rename: missing dependency '$cmd'" >&2
    exit 0
  fi
done

# Bail if missing session_id
if [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

# Path resolution: use transcript_path if available, otherwise scan
if [[ -z "$TRANSCRIPT_PATH" || ! -f "$TRANSCRIPT_PATH" ]]; then
  # Fallback: scan ~/.claude/projects for session file
  TRANSCRIPT_PATH=$(find ~/.claude/projects -name "${SESSION_ID}.jsonl" -type f 2>/dev/null | head -1)
  if [[ -z "$TRANSCRIPT_PATH" ]]; then
    log_error "$SESSION_ID" "Could not resolve transcript path"
    exit 0
  fi
fi

# --- Load config ---
load_config

# Check if disabled
if [[ "$CFG_ENABLED" != "true" ]]; then
  exit 0
fi

# --- Verify transcript exists ---
if [[ ! -f "$TRANSCRIPT_PATH" ]]; then
  log_error "$SESSION_ID" "Transcript not found: $TRANSCRIPT_PATH"
  exit 0
fi

# --- State management with flock ---
STATE_DIR="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}/state"
mkdir -p "$STATE_DIR"
STATE_FILE="$STATE_DIR/$SESSION_ID.json"
LOCK_FILE="$STATE_FILE.lock"

# Try to acquire lock (2 second timeout)
exec 200>"$LOCK_FILE"
if ! flock -w 2 200; then
  log_info "$SESSION_ID" "Could not acquire lock, skipping"
  exit 0
fi

# Load existing state
STATE=$(read_state "$STATE_FILE")
CURRENT_TITLE=$(echo "$STATE" | jq -r '.current_title // empty')
ORIGINAL_TITLE=$(echo "$STATE" | jq -r '.original_title // empty')
LAST_RENAMED_AT=$(echo "$STATE" | jq -r '.last_renamed_at_count // "0"')
STORED_MSG_COUNT=$(echo "$STATE" | jq -r '.message_count // "0"')

# --- Count current messages ---
MSG_COUNT=$(count_user_messages "$TRANSCRIPT_PATH")

# --- Decision logic ---

if [[ -z "$CURRENT_TITLE" ]]; then
  # FIRST RUN: no title yet
  FIRST_PROMPT=$(extract_first_user_prompt "$TRANSCRIPT_PATH")
  WORD_COUNT=$(count_words "$FIRST_PROMPT")

  if [[ "$WORD_COUNT" -lt "$CFG_MIN_FIRST_PROMPT_WORDS" ]]; then
    # Prompt too short — save state but don't name yet
    NEW_STATE=$(jq -cn \
      --arg mc "$MSG_COUNT" \
      --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      '{message_count: ($mc | tonumber), created_at: $ts}')
    write_state "$STATE_FILE" "$NEW_STATE"
    exit 0
  fi

  # Generate initial name
  log_info "$SESSION_ID" "Generating initial name (msg_count=$MSG_COUNT)"
  NEW_TITLE=$(generate_initial_name "$FIRST_PROMPT" "$CWD")

  if [[ -n "$NEW_TITLE" ]]; then
    write_session_title "$TRANSCRIPT_PATH" "$NEW_TITLE" "$SESSION_ID" || true
    NEW_STATE=$(jq -cn \
      --arg ct "$NEW_TITLE" \
      --arg ot "$NEW_TITLE" \
      --arg mc "$MSG_COUNT" \
      --arg lr "$MSG_COUNT" \
      --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      '{current_title: $ct, original_title: $ot, message_count: ($mc | tonumber), last_renamed_at_count: ($lr | tonumber), created_at: $ts}')
    write_state "$STATE_FILE" "$NEW_STATE"
    log_info "$SESSION_ID" "Initial title: '$NEW_TITLE'"
  fi

else
  # SUBSEQUENT RUN: check if update is needed
  MSGS_SINCE_LAST=$((MSG_COUNT - LAST_RENAMED_AT))

  if [[ "$MSGS_SINCE_LAST" -ge "$CFG_UPDATE_INTERVAL" ]]; then
    # Time to update
    log_info "$SESSION_ID" "Updating title (msgs_since_last=$MSGS_SINCE_LAST)"
    RECENT_CONTEXT=$(extract_recent_context "$TRANSCRIPT_PATH" 3)
    NEW_TITLE=$(generate_updated_name "$CURRENT_TITLE" "$ORIGINAL_TITLE" "$RECENT_CONTEXT")

    if [[ -n "$NEW_TITLE" ]]; then
      write_session_title "$TRANSCRIPT_PATH" "$NEW_TITLE" "$SESSION_ID" || true
      NEW_STATE=$(jq -cn \
        --arg ct "$NEW_TITLE" \
        --arg ot "$ORIGINAL_TITLE" \
        --arg mc "$MSG_COUNT" \
        --arg lr "$MSG_COUNT" \
        --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{current_title: $ct, original_title: $ot, message_count: ($mc | tonumber), last_renamed_at_count: ($lr | tonumber), created_at: $ts}')
      write_state "$STATE_FILE" "$NEW_STATE"
      log_info "$SESSION_ID" "Updated title: '$CURRENT_TITLE' -> '$NEW_TITLE'"
    fi
  else
    # Not time to update yet — just update message count and re-append current title
    write_session_title "$TRANSCRIPT_PATH" "$CURRENT_TITLE" "$SESSION_ID" || true
    NEW_STATE=$(echo "$STATE" | jq --arg mc "$MSG_COUNT" '.message_count = ($mc | tonumber)')
    write_state "$STATE_FILE" "$NEW_STATE"
  fi
fi
```

- [ ] **Step 5: Make scripts executable**

```bash
chmod +x scripts/rename-hook.sh scripts/generate-name.sh scripts/session-writer.sh scripts/utils.sh
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
bash tests/test-rename-hook.sh
```
Expected: All integration tests pass.

- [ ] **Step 7: Run full test suite**

```bash
bash tests/run-tests.sh
```
Expected: All test suites pass.

- [ ] **Step 8: Commit**

```bash
git add scripts/rename-hook.sh tests/test-rename-hook.sh tests/fixtures/hook-input-basic.json tests/fixtures/hook-input-short-prompt.json
git commit -m "feat: add main hook script with decision logic, state management, and flock"
```

---

## Task 6: On-Demand Skill (`skills/smart-rename/SKILL.md`)

**Files:**
- Create: `skills/smart-rename/SKILL.md`

- [ ] **Step 1: Write the skill markdown**

Create `skills/smart-rename/SKILL.md`:
````markdown
# Smart Rename

Intelligently rename the current Claude Code session based on conversation context.

## When This Skill Is Invoked

The user runs `/smart-rename` or asks to rename the current session intelligently.

## Instructions

When this skill is invoked, follow these steps:

1. **Analyze the conversation so far.** Look at:
   - The user's initial request (what started this session)
   - The main topics and files discussed
   - Any key actions taken (debugging, refactoring, feature work, etc.)

2. **Generate a concise session name** following these rules:
   - Use kebab-case (e.g., `fix-login-bug`, `refactor-auth-module`)
   - 2-5 words maximum
   - Focus on the ACTION and TARGET (what + where)
   - Be specific enough to distinguish from other sessions

3. **Present the suggested name to the user:**
   > Based on our conversation, I suggest renaming this session to: `suggested-name-here`
   >
   > This captures [brief explanation of why this name fits].
   >
   > Should I apply this name?

4. **If the user approves**, execute:
   ```
   /rename suggested-name-here
   ```

5. **If the user wants changes**, iterate on the name until they're satisfied, then apply.

## Examples

| Session Context | Suggested Name |
|---|---|
| Debugging a failing login form | `fix-login-validation` |
| Adding OAuth2 to an Express API | `add-oauth2-auth` |
| Refactoring database models | `refactor-db-models` |
| Writing unit tests for payments | `test-payment-module` |
| General project exploration | `explore-project-setup` |
````

- [ ] **Step 2: Commit**

```bash
git add skills/
git commit -m "feat: add /smart-rename on-demand skill"
```

---

## Task 7: README and Documentation

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

Create `README.md` — a compelling open-source README with:

**Structure:**
1. **Hero section** — Name, one-liner, badges (License, Version, "Works with Claude Code")
2. **Problem** — "You have 47 sessions named `quirky-blue-elephant`. Good luck finding your auth refactor."
3. **Solution** — 3-bullet summary of what the plugin does
4. **Demo** — Placeholder for GIF (`![Demo](docs/demo.gif)`)
5. **Install** — Single command: `/plugin marketplace add fe-bertholdo/smart-session-rename`
6. **How It Works** — Brief explanation of the hook + naming + evolution cycle
7. **Configuration** — Table of env vars and config file
8. **On-Demand** — How to use `/smart-rename`
9. **FAQ** — Common questions (cost, safety, uninstall)
10. **Contributing** — Link to CONTRIBUTING.md
11. **License** — MIT

The README should be concise, scannable, and have personality. Target: ~150 lines.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install instructions and configuration guide"
```

---

## Task 8: CI and GitHub Templates

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/ISSUE_TEMPLATE/bug_report.md`
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Create CI workflow**

Create `.github/workflows/ci.yml`:
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install jq
        run: sudo apt-get install -y jq
      - name: Run tests
        run: bash tests/run-tests.sh

  shellcheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install ShellCheck
        run: sudo apt-get install -y shellcheck
      - name: Lint scripts
        run: shellcheck scripts/*.sh tests/*.sh
```

- [ ] **Step 2: Create issue templates**

Create standard bug report and feature request templates.

- [ ] **Step 3: Create CONTRIBUTING.md**

Brief guide: fork, branch, test, PR. Mention `bash tests/run-tests.sh` and `shellcheck`.

- [ ] **Step 4: Commit**

```bash
git add .github/ CONTRIBUTING.md
git commit -m "chore: add CI workflow, issue templates, and contributing guide"
```

---

## Task 9: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
bash tests/run-tests.sh
```
Expected: All tests pass.

- [ ] **Step 2: Run shellcheck on all scripts**

```bash
shellcheck scripts/*.sh tests/*.sh
```
Expected: No errors.

- [ ] **Step 3: Verify plugin structure**

```bash
# Check all required files exist
ls -la .claude-plugin/plugin.json hooks/hooks.json scripts/*.sh skills/smart-rename/SKILL.md config/default-config.json README.md LICENSE
```

- [ ] **Step 4: Verify hooks.json references correct path**

```bash
cat hooks/hooks.json | jq '.hooks.Stop[0].hooks[0].command'
```
Expected: `"${CLAUDE_PLUGIN_ROOT}/scripts/rename-hook.sh"`

- [ ] **Step 5: Final commit with all remaining files**

```bash
git status
# If any unstaged files, add and commit
git add -A
git commit -m "chore: final verification — all tests pass, structure complete"
```
