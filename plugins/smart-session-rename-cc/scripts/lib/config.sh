#!/usr/bin/env bash
# lib/config.sh — config loading with precedence: env > user file > defaults
#
# Stateless implementation: each config_get call reads directly from JSON via jq.
# No associative arrays (declare -gA was observed to corrupt values in some Claude
# Code Bash tool environments — keys returned wrong values intermittently).
# Cost: ~10ms per jq call × ~10 calls per hook invocation ≈ 100ms total. Acceptable.

_config_env_var() {
  case "$1" in
    enabled)                   echo "SMART_RENAME_ENABLED" ;;
    model)                     echo "SMART_RENAME_MODEL" ;;
    max_budget_calls)          echo "SMART_RENAME_BUDGET_CALLS" ;;
    overflow_manual_slots)     echo "SMART_RENAME_OVERFLOW_SLOTS" ;;
    first_call_work_threshold) echo "SMART_RENAME_FIRST_THRESHOLD" ;;
    ongoing_work_threshold)    echo "SMART_RENAME_ONGOING_THRESHOLD" ;;
    reattach_interval)         echo "SMART_RENAME_REATTACH_INTERVAL" ;;
    circuit_breaker_threshold) echo "SMART_RENAME_CB_THRESHOLD" ;;
    lock_stale_seconds)        echo "SMART_RENAME_LOCK_STALE" ;;
    llm_timeout_seconds)       echo "SMART_RENAME_LLM_TIMEOUT" ;;
    log_level)                 echo "SMART_RENAME_LOG_LEVEL" ;;
    *)                         echo "" ;;
  esac
}

_config_defaults_file() {
  echo "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/config/default-config.json"
}

# config_load is kept for API compatibility (tests call it to force env re-read).
# With the stateless config_get, it's effectively a no-op — each config_get call
# reads fresh from disk + env every time.
config_load() {
  # No-op: stateless config_get reads directly each time.
  # Retained so existing code that calls config_load doesn't break.
  true
}

# Precedence: env var > user config file > defaults file.
config_get() {
  local key="$1"

  # 1. Check env override
  local env_name
  env_name="$(_config_env_var "$key")"
  if [[ -n "$env_name" && -n "${!env_name:-}" ]]; then
    echo "${!env_name}"
    return 0
  fi

  # 2. Check user config file (CLAUDE_PLUGIN_DATA/config.json)
  local user_file="${CLAUDE_PLUGIN_DATA:-}/config.json"
  if [[ -n "${CLAUDE_PLUGIN_DATA:-}" && -f "$user_file" ]]; then
    local val
    val=$(jq -r --arg k "$key" '.[$k] // empty' "$user_file" 2>/dev/null)
    if [[ -n "$val" ]]; then
      echo "$val"
      return 0
    fi
  fi

  # 3. Fall back to defaults
  local defaults_file
  defaults_file="$(_config_defaults_file)"
  if [[ -f "$defaults_file" ]]; then
    jq -r --arg k "$key" '.[$k] // empty' "$defaults_file" 2>/dev/null
  fi
}
