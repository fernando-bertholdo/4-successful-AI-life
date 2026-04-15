#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOTAL_PASS=0; TOTAL_FAIL=0

run_one() {
  local f="$1"
  echo ""
  echo "Running $(basename "$(dirname "$f")")/$(basename "$f")..."
  if bash "$f"; then
    ((TOTAL_PASS++)) || true
  else
    ((TOTAL_FAIL++)) || true
  fi
}

for test_file in "$SCRIPT_DIR"/unit/test-*.sh "$SCRIPT_DIR"/integration/test-*.sh; do
  [[ -f "$test_file" ]] && run_one "$test_file"
done

echo ""
echo "=============================="
echo "Test suites: $TOTAL_PASS passed, $TOTAL_FAIL failed"
[[ $TOTAL_FAIL -eq 0 ]] && exit 0 || exit 1
