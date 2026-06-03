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

echo "-- _sanitized_node_options strips --require pointing to missing files --"
# Repro of cmux issue: NODE_OPTIONS injects a preload .cjs whose path lives in
# $TMPDIR. When macOS evicts that file, every Node child crashes. The plugin must
# strip ONLY the broken --require, preserving other legitimate flags.
real_require=$(mktemp); printf '// noop\n' > "$real_require"
assert_eq "drops broken require, keeps memory flag" "--max-old-space-size=4096" \
  "$(export NODE_OPTIONS='--require=/var/folders/89/T/cmux-claude-node-options/restore-node-options.cjs --max-old-space-size=4096'; _sanitized_node_options)"
assert_eq "keeps require when file exists" "--require=$real_require --max-old-space-size=4096" \
  "$(export NODE_OPTIONS="--require=$real_require --max-old-space-size=4096"; _sanitized_node_options)"
assert_eq "all-broken require → empty" "" \
  "$(export NODE_OPTIONS='--require=/definitely/not/here.cjs'; _sanitized_node_options)"
assert_eq "empty NODE_OPTIONS → empty" "" \
  "$(export NODE_OPTIONS=''; _sanitized_node_options)"
assert_eq "unset NODE_OPTIONS → empty" "" \
  "$(unset NODE_OPTIONS; _sanitized_node_options)"
rm -f "$real_require"

echo "-- llm_generate_title invokes claude with sanitized NODE_OPTIONS --"
# Even when the parent shell carries a broken NODE_OPTIONS, the claude child must
# see a value with the bad --require stripped — otherwise the real Node binary
# crashes on startup before processing the prompt.
unset MOCK_CLAUDE_MODE
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"duration_ms":100,"total_cost_usd":0.001,"structured_output":{"domain":"x","clauses":["y"]}}]'
env_dump=$(mktemp)
export MOCK_CLAUDE_ENV_DUMP="$env_dump"
export NODE_OPTIONS="--require=/nope/missing.cjs --max-old-space-size=4096"
r=$(llm_generate_title "$ctx")
unset NODE_OPTIONS
assert_eq "call still succeeds with bad NODE_OPTIONS" "x" "$(echo "$r" | jq -r '.domain')"
observed=$(grep '^NODE_OPTIONS=' "$env_dump" | head -1 | sed 's/^NODE_OPTIONS=//')
assert_eq "child saw sanitized NODE_OPTIONS" "--max-old-space-size=4096" "$observed"
unset MOCK_CLAUDE_ENV_DUMP
rm -f "$env_dump"

unset MOCK_CLAUDE_MODE MOCK_CLAUDE_RESPONSE
rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
