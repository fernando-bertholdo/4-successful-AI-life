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
