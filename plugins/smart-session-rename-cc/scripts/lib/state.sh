#!/usr/bin/env bash
# lib/state.sh — session state JSON load/save + locking.
# Config resolution: uses config_get if config.sh is sourced, else falls back to env.

_state_file() {
  local sid="$1"
  local base="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}"
  mkdir -p "$base/state"
  echo "$base/state/$sid.json"
}

_state_lockdir() {
  echo "$(_state_file "$1").lockdir"
}

# Returns stale threshold seconds. Prefers config_get, falls back to env, then 60.
_state_lock_stale_seconds() {
  if declare -F config_get >/dev/null 2>&1; then
    local v; v=$(config_get lock_stale_seconds 2>/dev/null)
    [[ -n "$v" ]] && { echo "$v"; return 0; }
  fi
  echo "${SMART_RENAME_LOCK_STALE:-60}"
}

state_load() {
  local sid="$1"
  local f; f="$(_state_file "$sid")"
  if [[ ! -f "$f" ]]; then
    echo "{}"
    return 0
  fi
  if ! jq . "$f" >/dev/null 2>&1; then
    mv -f "$f" "${f}.corrupt.bak" 2>/dev/null || true
    echo "{}"
    return 0
  fi
  cat "$f"
}

state_save() {
  local sid="$1" json="$2"
  local f tmp
  f="$(_state_file "$sid")"
  tmp="${f}.tmp.$$"
  printf '%s\n' "$json" > "$tmp"
  mv -f "$tmp" "$f"
}

state_lock() {
  local sid="$1"
  local lockdir stale_seconds max_wait waited
  lockdir="$(_state_lockdir "$sid")"
  stale_seconds="$(_state_lock_stale_seconds)"
  max_wait=2
  waited=0

  if [[ -d "$lockdir" ]]; then
    local age
    age=$(( $(date +%s) - $(stat -f %m "$lockdir" 2>/dev/null || stat -c %Y "$lockdir") ))
    if [[ $age -ge $stale_seconds ]]; then
      rm -rf "$lockdir" 2>/dev/null || true
    fi
  fi

  while ! mkdir "$lockdir" 2>/dev/null; do
    if [[ $waited -ge $max_wait ]]; then
      return 1
    fi
    sleep 0.5
    waited=$((waited + 1))
  done
  return 0
}

state_unlock() {
  local sid="$1"
  rm -rf "$(_state_lockdir "$sid")" 2>/dev/null || true
}
