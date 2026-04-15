#!/usr/bin/env bash
# lib/scorer.sh — work-score + call/skip decision. Idempotency via signature.

# Args: turn_data_json
# Stdout: numeric delta
scorer_compute_delta() {
  local turn="$1"
  echo "$turn" | jq -r '
    ((.tool_call_count // 0)
     + ((.new_files_this_turn // []) | length) * 3
     + ((.user_word_count // 0) * 0.01))
  ' 2>/dev/null | awk '{ printf "%g\n", $1 }'
}

# Signature format: "<turn_number>:<file_size>"
# Same turn+size means the hook is re-entering for the same state → skip.
# Same turn but larger size = more content written since last run (agentic loop mid-turn) → proceed.

# Args: state_json, current_signature
# Stdout: {"decision":"call"|"skip","reason":"<string>"}
scorer_should_call_llm() {
  local state="$1" current_sig="$2"

  local last_sig
  last_sig=$(echo "$state" | jq -r '.last_processed_signature // ""')
  if [[ -n "$last_sig" && "$last_sig" == "$current_sig" ]]; then
    echo '{"decision":"skip","reason":"already_processed"}'
    return 0
  fi

  local frozen force_next llm_disabled has_title
  frozen=$(echo "$state" | jq -r '.frozen // false')
  force_next=$(echo "$state" | jq -r '.force_next // false')
  llm_disabled=$(echo "$state" | jq -r '.llm_disabled // false')
  has_title=$(echo "$state" | jq -r 'if .title_struct then "true" else "false" end')

  local calls_made overflow_used
  calls_made=$(echo "$state" | jq -r '.calls_made // 0')
  overflow_used=$(echo "$state" | jq -r '.overflow_used // 0')

  local max_calls overflow_slots
  max_calls=$(config_get max_budget_calls)
  overflow_slots=$(config_get overflow_manual_slots)

  local acc first_thr ongoing_thr
  acc=$(echo "$state" | jq -r '.accumulated_score // 0')
  first_thr=$(config_get first_call_work_threshold)
  ongoing_thr=$(config_get ongoing_work_threshold)

  if [[ "$frozen" == "true" ]]; then
    echo '{"decision":"skip","reason":"frozen"}'
    return 0
  fi

  if [[ "$force_next" == "true" ]]; then
    # Past budget: need an overflow slot
    if [[ "$calls_made" -ge "$max_calls" ]] && [[ "$overflow_used" -ge "$overflow_slots" ]]; then
      echo '{"decision":"skip","reason":"budget_and_overflow_exhausted"}'
      return 0
    fi
    echo '{"decision":"call","reason":"force_next"}'
    return 0
  fi

  if [[ "$llm_disabled" == "true" ]]; then
    echo '{"decision":"skip","reason":"llm_disabled_circuit_breaker"}'
    return 0
  fi

  if [[ "$calls_made" -ge "$max_calls" ]]; then
    echo '{"decision":"skip","reason":"budget_exhausted"}'
    return 0
  fi

  if [[ "$has_title" == "false" ]]; then
    if awk -v a="$acc" -v t="$first_thr" 'BEGIN { exit !(a >= t) }'; then
      echo '{"decision":"call","reason":"first_call_threshold"}'
      return 0
    fi
    echo '{"decision":"skip","reason":"below_first_threshold"}'
    return 0
  fi

  if awk -v a="$acc" -v t="$ongoing_thr" 'BEGIN { exit !(a >= t) }'; then
    echo '{"decision":"call","reason":"ongoing_threshold"}'
    return 0
  fi
  echo '{"decision":"skip","reason":"below_ongoing_threshold"}'
}
