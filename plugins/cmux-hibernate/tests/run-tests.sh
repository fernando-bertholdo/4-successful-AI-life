#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR/.."
python3 -m unittest discover -s tests/unit -p 'test_*.py' -v
