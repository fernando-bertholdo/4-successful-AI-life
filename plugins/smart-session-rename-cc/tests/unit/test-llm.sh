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
