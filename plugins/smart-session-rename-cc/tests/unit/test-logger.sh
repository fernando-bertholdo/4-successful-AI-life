#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/config.sh"
source "$SCRIPT_DIR/../../scripts/lib/logger.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }
assert_contains() { local d="$1" n="$2" h="$3"; [[ "$h" == *"$n"* ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d"; ((FAIL++)) || true; }; }

echo "=== logger.sh tests ==="
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
config_load

echo "-- emits valid JSONL --"
log_event info score_update "sess-a" '{"delta":6,"acc":18.5,"turn":14}'
logfile="$CLAUDE_PLUGIN_DATA/logs/sess-a.jsonl"
[[ -f "$logfile" ]] && { echo "  ✓ file exists"; ((PASS++)) || true; } || { echo "  ✗ missing"; ((FAIL++)) || true; }
line="$(head -1 "$logfile")"
assert_contains "has event" '"event":"score_update"' "$line"
assert_contains "has turn" '"turn":14' "$line"
echo "$line" | jq . >/dev/null 2>&1 && { echo "  ✓ valid JSON"; ((PASS++)) || true; } || { echo "  ✗ invalid JSON: $line"; ((FAIL++)) || true; }

echo "-- unsafe strings are escaped (quotes, newlines) --"
log_event info manual_rename_detected "sess-b" "$(jq -nc --arg t 'title with "quotes" and
newline' '{new_title:$t}')"
logfile="$CLAUDE_PLUGIN_DATA/logs/sess-b.jsonl"
line="$(head -1 "$logfile")"
echo "$line" | jq . >/dev/null 2>&1 && { echo "  ✓ valid JSON with unsafe content"; ((PASS++)) || true; } || { echo "  ✗ invalid: $line"; ((FAIL++)) || true; }

echo "-- level filter honors config --"
rm -f "$CLAUDE_PLUGIN_DATA/logs/sess-c.jsonl"
export SMART_RENAME_LOG_LEVEL=warn
config_load  # reload
log_event info suppressed "sess-c" '{}'
[[ ! -s "$CLAUDE_PLUGIN_DATA/logs/sess-c.jsonl" ]] && { echo "  ✓ info suppressed"; ((PASS++)) || true; } || { echo "  ✗ leaked"; ((FAIL++)) || true; }
log_event warn kept "sess-c" '{}'
grep -q kept "$CLAUDE_PLUGIN_DATA/logs/sess-c.jsonl" && { echo "  ✓ warn kept"; ((PASS++)) || true; } || { echo "  ✗ dropped"; ((FAIL++)) || true; }
unset SMART_RENAME_LOG_LEVEL

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
