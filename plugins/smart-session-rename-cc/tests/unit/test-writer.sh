#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/writer.sh"

PASS=0; FAIL=0
assert_eq() { local d="$1" e="$2" a="$3"; [[ "$e" == "$a" ]] && { echo "  ✓ $d"; ((PASS++)) || true; } || { echo "  ✗ $d: '$e' vs '$a'"; ((FAIL++)) || true; }; }

echo "=== writer.sh tests ==="
tmp=$(mktemp)
cat > "$tmp" <<'JSONL'
{"type":"user","message":{"role":"user","content":"hello"}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"hi"}]}}
JSONL

echo "-- append custom-title --"
writer_append_title "$tmp" "auth: fix jwt"
assert_eq "type" "custom-title" "$(tail -1 "$tmp" | jq -r '.type')"
assert_eq "customTitle" "auth: fix jwt" "$(tail -1 "$tmp" | jq -r '.customTitle')"

echo "-- second append adds second line --"
writer_append_title "$tmp" "auth: fix jwt, add tests"
assert_eq "two records" "2" "$(grep -c '"type":"custom-title"' "$tmp")"

echo "-- read last --"
assert_eq "last title" "auth: fix jwt, add tests" "$(writer_get_last_custom_title "$tmp")"

echo "-- missing transcript fails cleanly --"
if writer_append_title "/nonexistent.jsonl" "x" 2>/dev/null; then
  echo "  ✗ should fail"; ((FAIL++)) || true
else
  echo "  ✓ failed"; ((PASS++)) || true
fi

echo "-- get_last on file without custom-title returns empty --"
empty_file=$(mktemp)
echo '{"type":"user","message":{"role":"user","content":"x"}}' > "$empty_file"
assert_eq "empty" "" "$(writer_get_last_custom_title "$empty_file")"

echo "-- title with quotes/newlines is properly JSON-encoded --"
writer_append_title "$tmp" 'title with "quotes"'
assert_eq "quoted" 'title with "quotes"' "$(writer_get_last_custom_title "$tmp")"

echo "-- sessionId included when provided --"
writer_append_title "$tmp" "with-sid" "sess-123"
assert_eq "has sessionId" "sess-123" "$(tail -1 "$tmp" | jq -r '.sessionId')"
assert_eq "customTitle with sid" "with-sid" "$(tail -1 "$tmp" | jq -r '.customTitle')"

echo "-- sessionId absent when not provided --"
writer_append_title "$tmp" "no-sid"
assert_eq "no sessionId" "null" "$(tail -1 "$tmp" | jq -r '.sessionId')"

rm -f "$tmp" "$empty_file"
echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
