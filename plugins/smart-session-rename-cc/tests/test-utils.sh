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
    ((PASS++)) || true
  else
    echo "  ✗ $desc: expected '$expected', got '$actual'"
    ((FAIL++)) || true
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
