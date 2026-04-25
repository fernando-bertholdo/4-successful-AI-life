# Contributing to claude-code-smart-session-rename

Thanks for your interest in contributing!

## Development Setup

1. Clone the repo
2. Make your changes
3. Run tests: `bash tests/run-tests.sh`
4. Lint: `shellcheck scripts/*.sh`

## Pull Requests

- Fork the repo and create a feature branch
- Write tests for new functionality
- Ensure all tests pass and shellcheck is clean
- Open a PR with a clear description

## Code Style

- All scripts use `set -euo pipefail`
- Functions use `local` for variables
- Error handling: never crash the user's session — log and exit gracefully
- Use `jq` for JSON operations

## Testing

Tests use a simple assert-based framework in bash. Each test file sources the script being tested, uses `assert_eq` for comparisons, and cleans up temp files.

Run all tests: `bash tests/run-tests.sh`
