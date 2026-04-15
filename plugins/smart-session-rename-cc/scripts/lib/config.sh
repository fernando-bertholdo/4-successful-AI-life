#!/usr/bin/env bash
# lib/config.sh — config loading with precedence: env > user file > defaults

_CONFIG_LOADED=""
declare -gA _CONFIG_VALUES

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

config_load() {
  local defaults_file user_file
  defaults_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/config/default-config.json"
  user_file="${CLAUDE_PLUGIN_DATA:-}/config.json"

  _CONFIG_VALUES=()

  if [[ -f "$defaults_file" ]]; then
    while IFS=$'\t' read -r key val; do
      _CONFIG_VALUES["$key"]="$val"
    done < <(jq -r 'to_entries[] | "\(.key)\t\(.value)"' "$defaults_file" 2>/dev/null || true)
  fi

  if [[ -n "${CLAUDE_PLUGIN_DATA:-}" && -f "$user_file" ]]; then
    while IFS=$'\t' read -r key val; do
      _CONFIG_VALUES["$key"]="$val"
    done < <(jq -r 'to_entries[] | "\(.key)\t\(.value)"' "$user_file" 2>/dev/null || true)
  fi

  for key in "${!_CONFIG_VALUES[@]}"; do
    local env_name
    env_name="$(_config_env_var "$key")"
    if [[ -n "$env_name" && -n "${!env_name:-}" ]]; then
      _CONFIG_VALUES["$key"]="${!env_name}"
    fi
  done

  _CONFIG_LOADED=1
}

config_get() {
  local key="$1"
  [[ -z "$_CONFIG_LOADED" ]] && config_load
  echo "${_CONFIG_VALUES[$key]:-}"
}
