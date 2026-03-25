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
    ((PASS++)) || true
  else
    echo "  ✗ $desc: expected '$expected', got '$actual'"
    ((FAIL++)) || true
  fi
}

echo "=== session-writer.sh tests ==="

# Setup: create a fake session file
TMPDIR_TEST=$(mktemp -d)
FAKE_SESSION="$TMPDIR_TEST/test-session.jsonl"
echo '{"role":"user","type":"human","content":"test"}' > "$FAKE_SESSION"

# Test: write_session_title appends to file with correct format
echo "-- write_session_title --"
write_session_title "$FAKE_SESSION" "fix-auth-bug" "test-session-id"
last_line=$(tail -1 "$FAKE_SESSION")
echo "$last_line" | jq -e '.type == "custom-title"' > /dev/null 2>&1 \
  && { echo "  ✓ appends custom-title record"; ((PASS++)) || true; } \
  || { echo "  ✗ missing custom-title type: $last_line"; ((FAIL++)) || true; }

echo "$last_line" | jq -e '.customTitle == "fix-auth-bug"' > /dev/null 2>&1 \
  && { echo "  ✓ customTitle field correct"; ((PASS++)) || true; } \
  || { echo "  ✗ wrong customTitle: $last_line"; ((FAIL++)) || true; }

# Test: file now has 2 lines (original + title)
line_count=$(wc -l < "$FAKE_SESSION" | tr -d ' ')
assert_eq "file has 2 lines" "2" "$line_count"

# Test: writing again appends another record
write_session_title "$FAKE_SESSION" "updated-name" "test-session-id"
last_line=$(tail -1 "$FAKE_SESSION")
echo "$last_line" | jq -e '.customTitle == "updated-name"' > /dev/null 2>&1 \
  && { echo "  ✓ second write updates title"; ((PASS++)) || true; } \
  || { echo "  ✗ second write failed: $last_line"; ((FAIL++)) || true; }

# Test: writing to non-existent file returns 1 and logs error
echo "-- error handling --"
export CLAUDE_PLUGIN_DATA="$TMPDIR_TEST/plugin-data"
result=$(write_session_title "/nonexistent/path/session.jsonl" "test-name" "bad-session" 2>/dev/null; echo $?)
assert_eq "returns 1 on bad path" "1" "$result"

# Verify error was logged
if [[ -f "$CLAUDE_PLUGIN_DATA/logs/bad-session.log" ]]; then
  echo "  ✓ error logged to file"
  ((PASS++)) || true
else
  echo "  ✗ no error log created"
  ((FAIL++)) || true
fi

# Test: read-only file returns 1
READONLY_SESSION="$TMPDIR_TEST/readonly.jsonl"
echo '{"test":true}' > "$READONLY_SESSION"
chmod 444 "$READONLY_SESSION"
result=$(write_session_title "$READONLY_SESSION" "test" "readonly-session" 2>/dev/null; echo $?)
assert_eq "returns 1 on readonly file" "1" "$result"
chmod 644 "$READONLY_SESSION"

# Cleanup
rm -rf "$TMPDIR_TEST"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
