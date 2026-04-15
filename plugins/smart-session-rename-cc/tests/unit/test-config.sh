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
