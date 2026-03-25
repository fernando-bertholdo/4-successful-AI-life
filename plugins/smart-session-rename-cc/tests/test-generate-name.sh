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
    ((PASS++)) || true
  else
    echo "  ✗ $desc: expected '$expected', got '$actual'"
    ((FAIL++)) || true
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
echo "$result" | grep -q "integration tests" && { echo "  ✓ recent context has last message"; ((PASS++)) || true; } || { echo "  ✗ recent context missing last message"; ((FAIL++)) || true; }
echo "$result" | grep -q "API documentation" && { echo "  ✓ recent context has second-to-last"; ((PASS++)) || true; } || { echo "  ✗ recent context missing second-to-last"; ((FAIL++)) || true; }

# Test: count_user_messages
echo "-- count_user_messages --"
result=$(count_user_messages "$SCRIPT_DIR/fixtures/transcript-basic.jsonl")
assert_eq "basic has 1 user msg" "1" "$result"

result=$(count_user_messages "$SCRIPT_DIR/fixtures/transcript-multi-turn.jsonl")
assert_eq "multi-turn has 5 user msgs" "5" "$result"

# Test: parse_generated_name
echo "-- parse_generated_name --"
assert_eq "clean kebab" "fix-auth-middleware" "$(parse_generated_name "fix-auth-middleware")"
assert_eq "strips whitespace" "fix-auth" "$(parse_generated_name "  fix-auth  ")"
assert_eq "strips newlines" "refactor-login" "$(parse_generated_name $'refactor-login\n')"
assert_eq "reject spaces returns empty" "" "$(parse_generated_name "fix auth bug")"
assert_eq "reject empty" "" "$(parse_generated_name "")"
assert_eq "reject too long" "" "$(parse_generated_name "a-b-c-d-e-f-g")"
assert_eq "strips quotes" "fix-auth" "$(parse_generated_name '"fix-auth"')"

# Test: fallback_name
echo "-- fallback_name --"
result=$(fallback_name "I need to refactor the authentication middleware")
echo "$result" | grep -qE '^[a-z0-9-]+$' && { echo "  ✓ fallback is kebab-case"; ((PASS++)) || true; } || { echo "  ✗ fallback not kebab-case: $result"; ((FAIL++)) || true; }
word_count=$(echo "$result" | tr '-' '\n' | wc -l)
[[ "$word_count" -le 4 ]] && { echo "  ✓ fallback max 4 words"; ((PASS++)) || true; } || { echo "  ✗ fallback too long: $result ($word_count words)"; ((FAIL++)) || true; }

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
