#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOTAL_PASS=0
TOTAL_FAIL=0

for test_file in "$SCRIPT_DIR"/test-*.sh; do
  echo ""
  echo "Running $(basename "$test_file")..."
  if bash "$test_file"; then
    ((TOTAL_PASS++)) || true
  else
    ((TOTAL_FAIL++)) || true
  fi
done

echo ""
echo "=============================="
echo "Test suites: $TOTAL_PASS passed, $TOTAL_FAIL failed"
[[ $TOTAL_FAIL -eq 0 ]] && exit 0 || exit 1
