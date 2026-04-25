#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/config.sh"
source "$SCRIPT_DIR/../../scripts/lib/validate.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

echo "=== validate.sh tests ==="
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
config_load

echo "-- simple render --"
out='{"domain":"auth","clauses":["fix jwt expiry","add tests"]}'
s='{"rendered_title":"","manual_anchor":null,"manual_title_override":null}'
r=$(validate_and_render "$out" "$s")
assert_eq "title" "auth: fix jwt expiry, add tests" "$(echo "$r" | jq -r '.rendered_title')"
assert_eq "status" "ok" "$(echo "$r" | jq -r '.status')"

echo "-- identical → skip --"
s='{"rendered_title":"auth: fix jwt expiry, add tests","manual_anchor":null,"manual_title_override":null}'
assert_eq "skip identical" "skip_identical" "$(validate_and_render "$out" "$s" | jq -r '.status')"

echo "-- manual_anchor overrides domain only (clauses kept) --"
s='{"rendered_title":"","manual_anchor":"fernando-custom","manual_title_override":null}'
r=$(validate_and_render "$out" "$s")
assert_eq "anchor" "fernando-custom: fix jwt expiry, add tests" "$(echo "$r" | jq -r '.rendered_title')"

echo "-- manual_title_override renders verbatim (ignores LLM output) --"
s='{"rendered_title":"","manual_anchor":null,"manual_title_override":"My raw title with spaces"}'
r=$(validate_and_render "$out" "$s")
assert_eq "override verbatim" "My raw title with spaces" "$(echo "$r" | jq -r '.rendered_title')"
assert_eq "status ok" "ok" "$(echo "$r" | jq -r '.status')"

echo "-- dedupe clauses --"
out='{"domain":"auth","clauses":["fix jwt","  fix jwt  ","FIX JWT","add tests"]}'
s='{"rendered_title":"","manual_anchor":null,"manual_title_override":null}'
assert_eq "deduped" "auth: fix jwt, add tests" "$(validate_and_render "$out" "$s" | jq -r '.rendered_title')"

echo "-- invalid outputs --"
assert_eq "empty clauses" "invalid" "$(validate_and_render '{"domain":"x","clauses":[]}' "$s" | jq -r '.status')"
assert_eq "empty domain" "invalid" "$(validate_and_render '{"domain":"","clauses":["a"]}' "$s" | jq -r '.status')"

echo "-- error passes through --"
assert_eq "error" "error" "$(validate_and_render '{"error":"call_failed"}' "$s" | jq -r '.status')"

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
