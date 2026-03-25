#!/usr/bin/env bash
# utils.sh — Configuration loading, name validation, logging, JSON helpers
# Sourced by other scripts, never run directly.

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
DEFAULT_CONFIG="$PLUGIN_DIR/config/default-config.json"

# --- Config Loading ---
# Precedence: env vars > config file > defaults
load_config() {
  # Load defaults
  CFG_ENABLED="true"
  CFG_UPDATE_INTERVAL="3"
  CFG_MIN_FIRST_PROMPT_WORDS="10"
  CFG_MAX_TITLE_WORDS="5"

  # Override from config file if exists
  local config_file="${CLAUDE_PLUGIN_DATA:-}/config.json"
  if [[ -f "$config_file" ]]; then
    CFG_ENABLED=$(jq -r '.enabled // empty' "$config_file" 2>/dev/null || echo "")
    [[ -z "$CFG_ENABLED" ]] && CFG_ENABLED="true" || true

    local val
    val=$(jq -r '.update_interval // empty' "$config_file" 2>/dev/null || echo "")
    [[ -n "$val" ]] && CFG_UPDATE_INTERVAL="$val" || true

    val=$(jq -r '.min_first_prompt_words // empty' "$config_file" 2>/dev/null || echo "")
    [[ -n "$val" ]] && CFG_MIN_FIRST_PROMPT_WORDS="$val" || true

    val=$(jq -r '.max_title_words // empty' "$config_file" 2>/dev/null || echo "")
    [[ -n "$val" ]] && CFG_MAX_TITLE_WORDS="$val" || true
  fi

  # Override from env vars (highest priority)
  [[ -n "${SMART_RENAME_ENABLED:-}" ]] && CFG_ENABLED="$SMART_RENAME_ENABLED" || true
  [[ -n "${SMART_RENAME_UPDATE_INTERVAL:-}" ]] && CFG_UPDATE_INTERVAL="$SMART_RENAME_UPDATE_INTERVAL" || true
  [[ -n "${SMART_RENAME_MIN_WORDS:-}" ]] && CFG_MIN_FIRST_PROMPT_WORDS="$SMART_RENAME_MIN_WORDS" || true
  [[ -n "${SMART_RENAME_MAX_TITLE_WORDS:-}" ]] && CFG_MAX_TITLE_WORDS="$SMART_RENAME_MAX_TITLE_WORDS" || true
}

# --- Name Validation ---
# Returns 0 if valid, 1 if invalid
validate_name() {
  local name="$1"
  [[ -z "$name" ]] && return 1
  [[ "$name" =~ \  ]] && return 1
  local word_count
  word_count=$(echo "$name" | tr '-' '\n' | wc -l)
  [[ "$word_count" -gt 6 ]] && return 1
  return 0
}

# --- Word Counting ---
count_words() {
  local text="$1"
  [[ -z "$text" ]] && echo "0" && return
  echo "$text" | wc -w | tr -d ' '
}

# --- Logging ---
log_info() {
  local session_id="${1:-unknown}"
  local message="$2"
  local log_dir="${CLAUDE_PLUGIN_DATA:-/tmp}/logs"
  mkdir -p "$log_dir"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] INFO: $message" >> "$log_dir/$session_id.log"
}

log_error() {
  local session_id="${1:-unknown}"
  local message="$2"
  local log_dir="${CLAUDE_PLUGIN_DATA:-/tmp}/logs"
  mkdir -p "$log_dir"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: $message" >> "$log_dir/$session_id.log"
}

# --- State Management ---
write_state() {
  local state_file="$1"
  local content="$2"
  local state_dir
  state_dir="$(dirname "$state_file")"
  mkdir -p "$state_dir"
  local tmp_file
  tmp_file=$(mktemp "$state_dir/.tmp.XXXXXX")
  echo "$content" > "$tmp_file"
  mv "$tmp_file" "$state_file"
}

read_state() {
  local state_file="$1"
  if [[ -f "$state_file" ]]; then
    cat "$state_file"
  else
    echo '{}'
  fi
}
