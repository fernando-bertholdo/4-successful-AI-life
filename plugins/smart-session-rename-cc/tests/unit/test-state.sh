#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/state.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

echo "=== state.sh tests ==="
export CLAUDE_PLUGIN_DATA="$(mktemp -d)"
SID="sess-1"

echo "-- state_load on missing file returns {} --"
state=$(state_load "$SID")
assert_eq "empty load" "{}" "$state"

echo "-- state_save + state_load roundtrip --"
state_save "$SID" '{"version":"1.5","calls_made":3}'
state=$(state_load "$SID")
assert_eq "version" "1.5" "$(echo "$state" | jq -r '.version')"
assert_eq "calls_made" "3" "$(echo "$state" | jq -r '.calls_made')"

echo "-- no leftover tmp files --"
tmp_count=$(find "$CLAUDE_PLUGIN_DATA/state" -name '*.tmp*' 2>/dev/null | wc -l | tr -d ' ')
assert_eq "no tmp" "0" "$tmp_count"

echo "-- lock / unlock --"
state_lock "$SID" && { echo "  ✓ acquired"; ((PASS++)) || true; } || { echo "  ✗ failed"; ((FAIL++)) || true; }
[[ -d "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir" ]] && { echo "  ✓ lockdir exists"; ((PASS++)) || true; } || { echo "  ✗ missing"; ((FAIL++)) || true; }

echo "-- second lock attempt fails fast --"
start=$(date +%s)
if state_lock "$SID" 2>/dev/null; then
  echo "  ✗ second lock should fail"; ((FAIL++)) || true
else
  elapsed=$(($(date +%s) - start))
  [[ $elapsed -le 3 ]] && { echo "  ✓ failed within 3s"; ((PASS++)) || true; } || { echo "  ✗ too slow: ${elapsed}s"; ((FAIL++)) || true; }
fi

state_unlock "$SID"
[[ ! -d "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir" ]] && { echo "  ✓ released"; ((PASS++)) || true; } || { echo "  ✗ still held"; ((FAIL++)) || true; }

echo "-- stale lock cleaned (>= SMART_RENAME_LOCK_STALE seconds) --"
mkdir -p "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir"
# backdate 80s (exceeds default 60s stale threshold)
touch -t "$(date -v-80S +"%Y%m%d%H%M.%S" 2>/dev/null || date -u -d '80 seconds ago' +"%Y%m%d%H%M.%S")" "$CLAUDE_PLUGIN_DATA/state/$SID.json.lockdir"
state_lock "$SID" && { echo "  ✓ stale cleaned"; ((PASS++)) || true; } || { echo "  ✗ stale not cleaned"; ((FAIL++)) || true; }
state_unlock "$SID"

echo "-- corrupt state renames to .corrupt.bak and returns {} --"
echo "not valid json {" > "$CLAUDE_PLUGIN_DATA/state/$SID.json"
state=$(state_load "$SID")
assert_eq "corrupt resets" "{}" "$state"
[[ -f "$CLAUDE_PLUGIN_DATA/state/$SID.json.corrupt.bak" ]] && { echo "  ✓ backup saved"; ((PASS++)) || true; } || { echo "  ✗ backup missing"; ((FAIL++)) || true; }

echo "-- env fallback honored when config.sh not sourced --"
export SMART_RENAME_LOCK_STALE=120
# Re-source to pick up env; no config_get available
stale=$(_state_lock_stale_seconds)
assert_eq "env override" "120" "$stale"
unset SMART_RENAME_LOCK_STALE

rm -rf "$CLAUDE_PLUGIN_DATA"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
