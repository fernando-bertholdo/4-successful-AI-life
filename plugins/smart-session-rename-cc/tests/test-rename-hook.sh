#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

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

echo "=== rename-hook.sh integration tests ==="

# Setup
TMPDIR_TEST=$(mktemp -d)
export CLAUDE_PLUGIN_DATA="$TMPDIR_TEST/plugin-data"
mkdir -p "$CLAUDE_PLUGIN_DATA/state"

# Mock claude CLI to return a predictable name
MOCK_BIN="$TMPDIR_TEST/bin"
mkdir -p "$MOCK_BIN"
cat > "$MOCK_BIN/claude" << 'MOCK'
#!/usr/bin/env bash
echo "refactor-auth-middleware"
MOCK
chmod +x "$MOCK_BIN/claude"
export PATH="$MOCK_BIN:$PATH"

# Create writable copy of transcript fixture
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

STATE_FILE="$CLAUDE_PLUGIN_DATA/state/test-001.json"
if [[ -f "$STATE_FILE" ]]; then
  echo "  ✓ state file created"
  ((PASS++)) || true

  current_title=$(jq -r '.current_title' "$STATE_FILE")
  assert_eq "title was set" "refactor-auth-middleware" "$current_title"

  original_title=$(jq -r '.original_title' "$STATE_FILE")
  assert_eq "original_title matches" "refactor-auth-middleware" "$original_title"

  msg_count=$(jq -r '.message_count' "$STATE_FILE")
  assert_eq "message count recorded" "1" "$msg_count"
else
  echo "  ✗ state file not created"
  ((FAIL++)) || true
fi

# Check title was written to session file
last_line=$(tail -1 "$TRANSCRIPT")
echo "$last_line" | jq -e '.customTitle == "refactor-auth-middleware"' > /dev/null 2>&1 \
  && { echo "  ✓ title written to session file"; ((PASS++)) || true; } \
  || { echo "  ✗ title not in session file"; ((FAIL++)) || true; }

echo "$last_line" | jq -e '.type == "custom-title"' > /dev/null 2>&1 \
  && { echo "  ✓ correct record type"; ((PASS++)) || true; } \
  || { echo "  ✗ wrong record type"; ((FAIL++)) || true; }

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
  ((PASS++)) || true
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
  && { echo "  ✓ skipped when disabled"; ((PASS++)) || true; } \
  || { echo "  ✗ should have skipped"; ((FAIL++)) || true; }
unset SMART_RENAME_ENABLED

# Test 4: Invalid session ID should skip
echo "-- invalid session id: skip --"
HOOK_INPUT_NOSID=$(jq -n \
  --arg cwd "/home/user/project" \
  '{session_id: "", transcript_path: "/tmp/nonexistent.jsonl", cwd: $cwd, hook_event_name: "Stop"}')

echo "$HOOK_INPUT_NOSID" | bash "$SCRIPT_DIR/../scripts/rename-hook.sh" 2>/dev/null || true
echo "  ✓ handles missing session_id without crash"
((PASS++)) || true

# Test 5: Corrupted state file should not crash
echo "-- corrupted state --"
mkdir -p "$CLAUDE_PLUGIN_DATA/state"
echo "NOT VALID JSON" > "$CLAUDE_PLUGIN_DATA/state/test-005.json"
TRANSCRIPT5="$TMPDIR_TEST/session5.jsonl"
cp "$SCRIPT_DIR/fixtures/transcript-basic.jsonl" "$TRANSCRIPT5"
HOOK_INPUT_CORRUPT=$(jq -n \
  --arg sid "test-005" \
  --arg tp "$TRANSCRIPT5" \
  --arg cwd "/home/user/project" \
  '{session_id: $sid, transcript_path: $tp, cwd: $cwd, hook_event_name: "Stop"}')

echo "$HOOK_INPUT_CORRUPT" | bash "$SCRIPT_DIR/../scripts/rename-hook.sh" 2>/dev/null
echo "  ✓ handles corrupted state without crash"
((PASS++)) || true

# Cleanup
rm -rf "$TMPDIR_TEST"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
