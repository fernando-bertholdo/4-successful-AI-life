#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/transcript.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

FIX="$SCRIPT_DIR/../fixtures"
CWD="/tmp/fake-project"

echo "=== transcript.sh tests ==="

echo "-- single-turn feature --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-feature.jsonl" "[]" "$CWD")
assert_eq "turn_number" "1" "$(echo "$r" | jq -r '.turn_number')"
assert_eq "user_word_count" "7" "$(echo "$r" | jq -r '.user_word_count')"
assert_eq "tool_call_count" "4" "$(echo "$r" | jq -r '.tool_call_count')"
assert_eq "rate-limit in new files" "true" "$(echo "$r" | jq '[.new_files_this_turn[] | select(contains("rate-limit"))] | length > 0')"

echo "-- agentic multi-turn: only LAST user's turn --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-agentic.jsonl" "[]" "$CWD")
assert_eq "turn_number 2" "2" "$(echo "$r" | jq -r '.turn_number')"
assert_eq "tool_call_count 2" "2" "$(echo "$r" | jq -r '.tool_call_count')"

echo "-- multi-stop: multiple assistant entries in same turn aggregated --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-multi-stop.jsonl" "[]" "$CWD")
assert_eq "turn_number 1 (single user)" "1" "$(echo "$r" | jq -r '.turn_number')"
assert_eq "tool_call_count 3 (aggregated)" "3" "$(echo "$r" | jq -r '.tool_call_count')"

echo "-- new_files excludes previously seen --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-agentic.jsonl" '["src/auth/jwt.ts"]' "$CWD")
assert_eq "one new file" "1" "$(echo "$r" | jq -r '.new_files_this_turn | length')"

echo "-- user content as array (tool_result block) returns usable string --"
tmp=$(mktemp).jsonl
cat > "$tmp" <<'JSONL'
{"type":"user","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"x","content":"prev result"},{"type":"text","text":"Now fix the bug I mentioned"}]}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"d1","name":"Edit","input":{"file_path":"fix.ts"}}]}}
JSONL
r=$(transcript_parse_current_turn "$tmp" "[]" "$CWD")
assert_eq "user_msg extracted from array" "Now fix the bug I mentioned" "$(echo "$r" | jq -r '.user_msg')"
rm -f "$tmp"

echo "-- domain_guess from file paths (second level) --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-agentic.jsonl" "[]" "$CWD")
assert_eq "domain_guess auth" "auth" "$(echo "$r" | jq -r '.domain_guess')"

echo "-- cwd fallback when no files --"
tmp=$(mktemp).jsonl
cat > "$tmp" <<'JSONL'
{"type":"user","message":{"role":"user","content":"hi"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"hello"}]}}
JSONL
r=$(transcript_parse_current_turn "$tmp" "[]" "/tmp/my-project")
assert_eq "domain_guess from cwd" "my-project" "$(echo "$r" | jq -r '.domain_guess')"
rm -f "$tmp"

echo "-- file_size exposed for idempotency signature --"
r=$(transcript_parse_current_turn "$FIX/transcript-v15-feature.jsonl" "[]" "$CWD")
fs=$(echo "$r" | jq -r '.file_size')
[[ "$fs" -gt 100 ]] && { echo "  ✓ file_size > 100 ($fs)"; ((PASS++)) || true; } || { echo "  ✗ unexpected file_size: $fs"; ((FAIL++)) || true; }

echo "-- missing transcript returns error field --"
r=$(transcript_parse_current_turn "/nonexistent.jsonl" "[]" "$CWD" || true)
assert_eq "error field" "missing_transcript" "$(echo "$r" | jq -r '.error // ""')"

echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
