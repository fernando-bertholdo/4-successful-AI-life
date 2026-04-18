#!/usr/bin/env bash
# lib/llm.sh — wrapper around claude -p with --json-schema.
# Portable timeout (timeout/gtimeout/perl fallback). jq-based prompt rendering (multiline-safe).

_LLM_JSON_SCHEMA='{
  "type":"object",
  "properties":{
    "domain":{"type":"string","minLength":1,"maxLength":30},
    "clauses":{"type":"array","items":{"type":"string","minLength":2,"maxLength":50},"minItems":1,"maxItems":5}
  },
  "required":["domain","clauses"],
  "additionalProperties":false
}'

# Picks timeout command: timeout | gtimeout | perl-based | none (no-op)
_llm_timeout_wrapper() {
  local seconds="$1"
  if command -v timeout >/dev/null 2>&1; then
    echo "timeout $seconds"
  elif command -v gtimeout >/dev/null 2>&1; then
    echo "gtimeout $seconds"
  elif command -v perl >/dev/null 2>&1; then
    # perl -e 'alarm shift; exec @ARGV' -- N cmd args...
    echo "perl -e alarm_shift_exec $seconds"
  else
    echo ""
  fi
}

# Runs a command with timeout using the best available wrapper.
# Args: seconds, command, args...
_llm_with_timeout() {
  local seconds="$1"; shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$seconds" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$seconds" "$@"
  elif command -v perl >/dev/null 2>&1; then
    perl -e 'alarm shift; exec @ARGV' "$seconds" "$@"
  else
    "$@"
  fi
}

# Render prompt template with variable substitution. jq-based, handles multiline/quotes/slashes.
_render_prompt() {
  local ctx_json="$1"
  local template_file
  template_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/prompts/generation.md"
  [[ ! -f "$template_file" ]] && return 1

  jq -nr --rawfile tmpl "$template_file" --argjson ctx "$ctx_json" '
    $ctx
    | to_entries
    | reduce .[] as $e ($tmpl;
        gsub("\\$\\{" + $e.key + "\\}"; ($e.value | tostring))
      )
  '
}

llm_generate_title() {
  local ctx_json="$1"
  local prompt
  prompt=$(_render_prompt "$ctx_json") || { echo '{"error":"prompt_template_missing"}'; return 1; }

  local model timeout_s
  model=$(config_get model)
  timeout_s=$(config_get llm_timeout_seconds)

  local raw rc stderr_file=""
  # Capture stderr when debugging (normally suppressed to avoid polluting output)
  if [[ -n "${SMART_RENAME_DEBUG:-}" ]]; then
    stderr_file="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}/llm-stderr.log"
    echo "[debug] llm cmd: claude -p --model $model --output-format json --no-session-persistence --json-schema <schema> <prompt-len=${#prompt}>" >&2
  fi
  raw=$(_llm_with_timeout "$timeout_s" claude -p \
    --model "$model" \
    --output-format json \
    --no-session-persistence \
    --json-schema "$_LLM_JSON_SCHEMA" \
    "$prompt" 2>"${stderr_file:-/dev/null}")
  rc=$?

  if [[ -n "$stderr_file" && -s "$stderr_file" ]]; then
    echo "[debug] claude stderr:" >&2
    head -20 "$stderr_file" >&2
  fi

  if [[ $rc -ne 0 ]]; then
    [[ -n "${SMART_RENAME_DEBUG:-}" ]] && echo "[debug] claude exit code: $rc" >&2
    echo '{"error":"call_failed"}'
    return 1
  fi

  if ! echo "$raw" | jq . >/dev/null 2>&1; then
    echo '{"error":"invalid_output"}'
    return 1
  fi

  local is_error
  is_error=$(echo "$raw" | jq -r '[.[] | select(.type == "result")] | first | .is_error // false')
  if [[ "$is_error" == "true" ]]; then
    echo '{"error":"call_failed"}'
    return 1
  fi

  local output
  output=$(echo "$raw" | jq -c '[.[] | select(.type == "result")] | first | .structured_output // empty')
  if [[ -z "$output" || "$output" == "null" ]]; then
    echo '{"error":"invalid_output"}'
    return 1
  fi

  local cost duration
  cost=$(echo "$raw" | jq -r '[.[] | select(.type == "result")] | first | .total_cost_usd // 0')
  duration=$(echo "$raw" | jq -r '[.[] | select(.type == "result")] | first | .duration_ms // 0')

  echo "$output" | jq --arg c "$cost" --arg d "$duration" \
    '. + {_cost_usd: ($c | tonumber), _duration_ms: ($d | tonumber)}'
}
