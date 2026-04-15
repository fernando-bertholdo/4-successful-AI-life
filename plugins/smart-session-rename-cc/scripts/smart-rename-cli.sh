#!/usr/bin/env bash
# smart-rename-cli.sh — skill subcommand dispatcher (Phase 1: freeze/unfreeze only)
#
# Session id resolution (in priority order):
#   1. $CLAUDE_SESSION_ID env var (set by hooks; usually NOT set when invoked from a skill)
#   2. transcript path arg ($1) → derive from .jsonl filename
#   3. cwd-derive: scan ~/.claude/projects/<encoded-pwd>/ for the most recent .jsonl
#
# Encoding rule (observed empirically from Claude Code CLI v2.1.85):
#   - Resolve symlinks via `pwd -P` (matters on macOS where /tmp is /private/tmp)
#   - Strip leading `/`
#   - Replace every `/` AND `_` with `-`
#   - Prepend a single `-`
# Example: /Users/x/tech_projects/foo  →  -Users-x-tech-projects-foo
#
# Set SMART_RENAME_DEBUG=1 to print resolution steps to stderr.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/state.sh"

_dbg() { [[ -n "${SMART_RENAME_DEBUG:-}" ]] && echo "[debug] $*" >&2 || true; }

_encode_cwd() {
  local p="${1:-$(pwd -P)}"
  echo "-$(echo "$p" | sed 's|^/||' | tr '/_' '--')"
}

_session_id_from_cwd() {
  local encoded proj_dir latest
  encoded="$(_encode_cwd)"
  proj_dir="$HOME/.claude/projects/$encoded"
  _dbg "cwd=$(pwd -P)"
  _dbg "encoded=$encoded"
  _dbg "proj_dir=$proj_dir (exists=$([[ -d "$proj_dir" ]] && echo yes || echo no))"
  [[ -d "$proj_dir" ]] || return 1
  latest="$(ls -t "$proj_dir"/*.jsonl 2>/dev/null | head -1)"
  _dbg "latest_jsonl=$latest"
  [[ -z "$latest" ]] && return 1
  basename "$latest" .jsonl
}

session_id_from_args() {
  if [[ -n "${CLAUDE_SESSION_ID:-}" ]]; then
    _dbg "source=env CLAUDE_SESSION_ID"
    echo "$CLAUDE_SESSION_ID"; return 0
  fi
  if [[ -n "${1:-}" && -f "$1" ]]; then
    _dbg "source=arg transcript_path=$1"
    basename "$1" .jsonl; return 0
  fi
  local sid; sid="$(_session_id_from_cwd)" || true
  if [[ -n "$sid" ]]; then
    _dbg "source=cwd-derive"
    echo "$sid"; return 0
  fi
  return 1
}

cmd="${1:-}"; shift || true

case "$cmd" in
  freeze|unfreeze)
    sid="$(session_id_from_args "${1:-}")"
    if [[ -z "$sid" ]]; then
      echo "ERROR: cannot determine session id" >&2
      echo "  Tried: \$CLAUDE_SESSION_ID, transcript_path arg, cwd-derive from $(pwd -P)" >&2
      echo "  Run with SMART_RENAME_DEBUG=1 for resolution trace." >&2
      exit 1
    fi
    state_lock "$sid" || { echo "ERROR: could not lock"; exit 1; }
    trap "state_unlock $sid" EXIT
    state=$(state_load "$sid")
    if [[ "$cmd" == "freeze" ]]; then
      new_state=$(echo "$state" | jq '.frozen = true | .updated_at = (now | todate)')
      echo "Smart rename: FROZEN for session $sid"
    else
      new_state=$(echo "$state" | jq '.frozen = false | .updated_at = (now | todate)')
      echo "Smart rename: UNFROZEN for session $sid"
    fi
    state_save "$sid" "$new_state"
    ;;
  *)
    echo "Phase 1 prototype — only freeze/unfreeze supported."
    exit 1
    ;;
esac
