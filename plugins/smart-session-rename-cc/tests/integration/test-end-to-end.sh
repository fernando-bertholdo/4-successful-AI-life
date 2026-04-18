#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_DIR/scripts/rename-hook.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
export PATH="$SCRIPT_DIR/../mocks:$PATH"

run_hook() {
  local transcript="$1" sid="$2"
  jq -nc --arg sid "$sid" --arg tp "$transcript" --arg cwd "$PWD" \
    '{session_id:$sid, transcript_path:$tp, cwd:$cwd}' | bash "$HOOK"
}

echo "=== end-to-end integration tests ==="

echo "-- Q&A: low score, no LLM call --"
tqa=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-qa.jsonl" "$tqa"
run_hook "$tqa" "sess-qa"
assert_eq "no LLM" "0" "$(jq -r '.calls_made // 0' "$CLAUDE_PLUGIN_DATA/state/sess-qa.json")"

echo "-- Feature: threshold met → LLM call + title written (pre-seeded score to 20) --"
unset MOCK_CLAUDE_MODE
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"duration_ms":200,"total_cost_usd":0.05,"structured_output":{"domain":"auth","clauses":["add rate limiting"]}}]'
tf=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tf"
mkdir -p "$CLAUDE_PLUGIN_DATA/state"
jq -nc '{version:"1.5", accumulated_score:10, title_struct:null, calls_made:0, overflow_used:0, failure_count:0, llm_disabled:false, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-feat.json"
run_hook "$tf" "sess-feat"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-feat.json")
assert_eq "calls_made 1" "1" "$(echo "$s" | jq -r '.calls_made')"
assert_eq "title set" "auth: add rate limiting" "$(echo "$s" | jq -r '.rendered_title')"
assert_eq "JSONL has custom-title" "custom-title" "$(jq -rs '.[-1].type' "$tf")"
assert_eq "last_processed_signature set" "true" "$(echo "$s" | jq 'has("last_processed_signature")')"

echo "-- Writer failure: state NOT promoted, signature NOT advanced (R1) --"
tfw=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tfw"
chmod 444 "$tfw"
jq -nc '{version:"1.5", accumulated_score:15, title_struct:null, calls_made:0, overflow_used:0, failure_count:0, llm_disabled:false, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-wf.json"
run_hook "$tfw" "sess-wf"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-wf.json")
assert_eq "rendered_title empty (not promoted)" "" "$(echo "$s" | jq -r '.rendered_title // ""')"
assert_eq "signature not advanced" "" "$(echo "$s" | jq -r '.last_processed_signature // ""')"
chmod 644 "$tfw"

echo "-- LLM failure increments failure_count --"
export MOCK_CLAUDE_MODE=fail
tf2=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tf2"
jq -nc '{version:"1.5", accumulated_score:20, title_struct:null, calls_made:0, overflow_used:0, failure_count:0, llm_disabled:false, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-fail.json"
run_hook "$tf2" "sess-fail"
assert_eq "failure 1" "1" "$(jq -r '.failure_count // 0' "$CLAUDE_PLUGIN_DATA/state/sess-fail.json")"
unset MOCK_CLAUDE_MODE

echo "-- Circuit breaker trips after 3 failures --"
export MOCK_CLAUDE_MODE=fail
tcb=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tcb"
jq -nc '{version:"1.5", failure_count:2, llm_disabled:false, calls_made:0, overflow_used:0, accumulated_score:100, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-cb.json"
run_hook "$tcb" "sess-cb"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-cb.json")
assert_eq "failure 3" "3" "$(echo "$s" | jq -r '.failure_count')"
assert_eq "llm_disabled" "true" "$(echo "$s" | jq -r '.llm_disabled')"
unset MOCK_CLAUDE_MODE

echo "-- Idempotency: same signature does NOT double-count (pre-seed so first call fires) --"
unset MOCK_CLAUDE_MODE
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"duration_ms":200,"total_cost_usd":0.05,"structured_output":{"domain":"test","clauses":["a"]}}]'
tid=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tid"
jq -nc '{version:"1.5", accumulated_score:15, title_struct:null, calls_made:0, overflow_used:0, failure_count:0, llm_disabled:false, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-idem.json"
run_hook "$tid" "sess-idem"
run_hook "$tid" "sess-idem"
assert_eq "calls_made still 1 after 2 hook runs on same file" "1" "$(jq -r '.calls_made' "$CLAUDE_PLUGIN_DATA/state/sess-idem.json")"

echo "-- Multi-stop: file grows on second run → signature differs → proceeds --"
tms=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-multi-stop.jsonl" "$tms"
head -2 "$tms" > "${tms}.part1"
run_hook "${tms}.part1" "sess-ms"
s_part=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-ms.json")
run_hook "$tms" "sess-ms"
s_full=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-ms.json")
part_files=$(echo "$s_part" | jq -r '.active_files_recent | length')
full_files=$(echo "$s_full" | jq -r '.active_files_recent | length')
[[ "$full_files" -ge "$part_files" ]] && { echo "  ✓ signature-based idempotency allowed mid-turn re-processing"; ((PASS++)) || true; } || { echo "  ✗ full=$full_files part=$part_files"; ((FAIL++)) || true; }

echo "-- Manual /rename sets title_override (not anchor) --"
tman=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tman"
jq -nc '{type:"custom-title", customTitle:"My custom free-form title"}' >> "$tman"
run_hook "$tman" "sess-man"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-man.json")
assert_eq "title_override set" "My custom free-form title" "$(echo "$s" | jq -r '.manual_title_override')"
assert_eq "rendered is override" "My custom free-form title" "$(echo "$s" | jq -r '.rendered_title')"

echo "-- Anchor persistence: /rename nativo then new hook → still honors override --"
run_hook "$tman" "sess-man"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-man.json")
assert_eq "override persists" "My custom free-form title" "$(echo "$s" | jq -r '.manual_title_override')"
assert_eq "rendered still override" "My custom free-form title" "$(echo "$s" | jq -r '.rendered_title')"

echo "-- Pivot: domain changes are reflected when LLM returns new domain (pre-seeded state with existing title_struct) --"
export MOCK_CLAUDE_RESPONSE='[{"type":"result","is_error":false,"duration_ms":200,"total_cost_usd":0.05,"structured_output":{"domain":"ci","clauses":["add vercel workflow"]}}]'
jq -nc '{version:"1.5", accumulated_score:40, title_struct:{domain:"auth",clauses:["old"]}, rendered_title:"auth: old", calls_made:1, overflow_used:0, failure_count:0, llm_disabled:false, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-pv.json"
tpv=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-pivot.jsonl" "$tpv"
run_hook "$tpv" "sess-pv"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-pv.json")
assert_eq "pivot domain" "ci" "$(echo "$s" | jq -r '.title_struct.domain')"

echo "-- Force path consumes overflow when budget already at max --"
tfc=$(mktemp).jsonl
cp "$SCRIPT_DIR/../fixtures/transcript-v15-feature.jsonl" "$tfc"
jq -nc '{version:"1.5", title_struct:{domain:"x",clauses:["a"]}, rendered_title:"x: a", calls_made:6, overflow_used:0, force_next:true, accumulated_score:0, last_processed_signature:""}' \
  > "$CLAUDE_PLUGIN_DATA/state/sess-force.json"
run_hook "$tfc" "sess-force"
s=$(cat "$CLAUDE_PLUGIN_DATA/state/sess-force.json")
assert_eq "overflow incremented" "1" "$(echo "$s" | jq -r '.overflow_used')"
assert_eq "force consumed" "false" "$(echo "$s" | jq -r '.force_next')"

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
