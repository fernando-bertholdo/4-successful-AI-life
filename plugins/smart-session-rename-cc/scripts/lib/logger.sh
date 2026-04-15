#!/usr/bin/env bash
# lib/logger.sh — structured JSONL logging per session. Uses config_get for log_level.

_log_level_rank() {
  case "$1" in
    debug) echo 0 ;; info) echo 1 ;; warn) echo 2 ;; error) echo 3 ;;
    *) echo 1 ;;
  esac
}

# Args: level event_type session_id data_json
# data_json must be valid JSON produced via jq -nc --arg ... (never string-interpolated).
log_event() {
  local level="$1" event="$2" session_id="$3" data="${4:-\{\}}"

  local cur_level="info"
  if declare -F config_get >/dev/null 2>&1; then
    local v; v=$(config_get log_level 2>/dev/null)
    [[ -n "$v" ]] && cur_level="$v"
  elif [[ -n "${SMART_RENAME_LOG_LEVEL:-}" ]]; then
    cur_level="$SMART_RENAME_LOG_LEVEL"
  fi

  if [[ "$(_log_level_rank "$level")" -lt "$(_log_level_rank "$cur_level")" ]]; then
    return 0
  fi

  local base_dir log_dir log_file ts
  base_dir="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}"
  log_dir="$base_dir/logs"
  mkdir -p "$log_dir"
  log_file="$log_dir/$session_id.jsonl"
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  jq -nc \
    --arg ts "$ts" --arg level "$level" --arg event "$event" \
    --argjson data "$data" \
    '{ts: $ts, level: $level, event: $event} + $data' \
    >> "$log_file" 2>/dev/null || true
}
