#!/usr/bin/env bash
# rename-hook.sh — v1.5 Stop hook orchestrator.
# Input: stdin JSON {session_id, transcript_path, cwd}.
# Contract: always exits 0; never blocks the user's session.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/config.sh"
source "$SCRIPT_DIR/lib/state.sh"
source "$SCRIPT_DIR/lib/logger.sh"
source "$SCRIPT_DIR/lib/transcript.sh"
source "$SCRIPT_DIR/lib/scorer.sh"
source "$SCRIPT_DIR/lib/llm.sh"
source "$SCRIPT_DIR/lib/validate.sh"
source "$SCRIPT_DIR/lib/writer.sh"

# --- Traps split: EXIT unlocks only; ERR logs crash (with sentinel to avoid double-logging) ---
# --- Traps: EXIT captures $? at entry (before state_unlock mutates it) ---
# Invariant: every early `exit 0` path MUST set _HOOK_CLEAN_EXIT=1. Adding a new exit
# path that forgets the sentinel would cause false hook_crashed logs.
_HOOK_CLEAN_EXIT=""
_cleanup_exit() {
  local rc=$?                     # capture status FIRST, before any command below mutates it
  [[ -n "${SESSION_ID:-}" ]] && state_unlock "$SESSION_ID" 2>/dev/null || true
  if [[ -z "$_HOOK_CLEAN_EXIT" && $rc -ne 0 ]]; then
    [[ -n "${SESSION_ID:-}" ]] && log_event error hook_crashed "$SESSION_ID" "$(jq -nc --argjson rc "$rc" '{exit_code:$rc}' 2>/dev/null || echo '{}')" || true
  fi
}
trap _cleanup_exit EXIT

# --- 1. Check dependencies BEFORE any jq usage (jq needed for log_event) ---
if ! command -v jq >/dev/null 2>&1; then
  # Cannot log without jq; silent exit
  _HOOK_CLEAN_EXIT=1; exit 0
fi

# --- 2. Parse input ---
INPUT_RAW="$(cat)"
SESSION_ID="$(echo "$INPUT_RAW" | jq -r '.session_id // empty' 2>/dev/null)"
TRANSCRIPT_PATH="$(echo "$INPUT_RAW" | jq -r '.transcript_path // empty' 2>/dev/null)"
CWD="$(echo "$INPUT_RAW" | jq -r '.cwd // empty' 2>/dev/null)"

if [[ -z "$SESSION_ID" || -z "$TRANSCRIPT_PATH" ]]; then
  _HOOK_CLEAN_EXIT=1; exit 0
fi

command -v claude >/dev/null 2>&1 || { log_event error missing_dep "$SESSION_ID" '{"dep":"claude"}'; _HOOK_CLEAN_EXIT=1; exit 0; }

if [[ ! -r "$TRANSCRIPT_PATH" ]]; then
  log_event warn transcript_missing "$SESSION_ID" '{}'
  _HOOK_CLEAN_EXIT=1; exit 0
fi

config_load
if [[ "$(config_get enabled)" != "true" ]]; then
  _HOOK_CLEAN_EXIT=1; exit 0
fi

# --- 2. Lock + load state ---
if ! state_lock "$SESSION_ID"; then
  log_event info lock_contention "$SESSION_ID" '{}'
  _HOOK_CLEAN_EXIT=1; exit 0
fi

STATE="$(state_load "$SESSION_ID")"

# --- 3. Detect /rename nativo → manual_title_override (not manual_anchor) ---
LAST_JSONL_TITLE="$(writer_get_last_custom_title "$TRANSCRIPT_PATH")"
LAST_PLUGIN_TITLE="$(echo "$STATE" | jq -r '.last_plugin_written_title // ""')"
if [[ -n "$LAST_JSONL_TITLE" && "$LAST_JSONL_TITLE" != "$LAST_PLUGIN_TITLE" ]]; then
  STATE=$(echo "$STATE" | jq --arg t "$LAST_JSONL_TITLE" '
    .manual_title_override = $t
    | .rendered_title = $t
    | .last_plugin_written_title = $t
  ')
  log_event info manual_rename_detected "$SESSION_ID" "$(jq -nc --arg t "$LAST_JSONL_TITLE" '{new_title:$t}')"
fi

# --- 4. Parse transcript (with cwd) ---
PREV_FILES=$(echo "$STATE" | jq -c '.active_files_recent // []')
TURN=$(transcript_parse_current_turn "$TRANSCRIPT_PATH" "$PREV_FILES" "$CWD")
TURN_NUM=$(echo "$TURN" | jq -r '.turn_number // 0')
FILE_SIZE=$(echo "$TURN" | jq -r '.file_size // 0')
CURRENT_SIGNATURE="${TURN_NUM}:${FILE_SIZE}"

# --- 5. Compute work score delta + update active_files (no last_processed_signature yet!) ---
DELTA=$(scorer_compute_delta "$TURN")
STATE=$(echo "$STATE" | jq \
  --argjson turn "$TURN" \
  --argjson d "$DELTA" '
  .accumulated_score = ((.accumulated_score // 0) + $d)
  | .domain_guess = ($turn.domain_guess // .domain_guess)
  | .active_files_recent = (
      ((.active_files_recent // []) + ($turn.all_files_touched // []))
      | unique | .[0:20]
    )
  | .branch = ($turn.branch // .branch // "")
  | .updated_at = (now | todate)
  | .version = "1.5"
')

log_event debug score_update "$SESSION_ID" "$(jq -nc --argjson d "$DELTA" --argjson acc "$(echo "$STATE" | jq -r '.accumulated_score')" --argjson t "$TURN_NUM" --argjson fs "$FILE_SIZE" '{delta:$d, acc:$acc, turn:$t, file_size:$fs}')"

# --- 6. Decide (scorer reads last_processed_signature, which still holds the PREVIOUS value) ---
DECISION_JSON=$(scorer_should_call_llm "$STATE" "$CURRENT_SIGNATURE")
DECISION=$(echo "$DECISION_JSON" | jq -r '.decision')
REASON=$(echo "$DECISION_JSON" | jq -r '.reason')

log_event info llm_decision "$SESSION_ID" "$(jq -nc --arg d "$DECISION" --arg r "$REASON" '{decision:$d, reason:$r}')"

REATTACH_INTERVAL=$(config_get reattach_interval)
CUR_TITLE=$(echo "$STATE" | jq -r '.rendered_title // ""')

if [[ "$DECISION" == "skip" ]]; then
  # Periodic re-attach
  if [[ -n "$CUR_TITLE" ]] && (( TURN_NUM % REATTACH_INTERVAL == 0 )); then
    if writer_append_title "$TRANSCRIPT_PATH" "$CUR_TITLE"; then
      log_event info title_reattached "$SESSION_ID" "$(jq -nc --arg t "$CUR_TITLE" '{title:$t}')"
    fi
  fi
  # Update signature AFTER decision
  STATE=$(echo "$STATE" | jq --arg s "$CURRENT_SIGNATURE" '.last_processed_signature = $s')
  state_save "$SESSION_ID" "$STATE"
  _HOOK_CLEAN_EXIT=1; exit 0
fi

# --- 7. Call LLM ---
CALLS_MADE=$(echo "$STATE" | jq -r '.calls_made // 0')
MAX_CALLS=$(config_get max_budget_calls)

# Decide whether this consumes a budget slot or an overflow slot (force_next past budget)
if [[ "$CALLS_MADE" -ge "$MAX_CALLS" ]]; then
  STATE=$(echo "$STATE" | jq '.overflow_used = ((.overflow_used // 0) + 1) | .force_next = false')
else
  STATE=$(echo "$STATE" | jq '.calls_made = ((.calls_made // 0) + 1) | .force_next = false')
fi

# Build LLM context (recent_turns: array of transition titles, joined safely in jq)
CTX=$(jq -nc \
  --arg t "$CUR_TITLE" \
  --arg a "$(echo "$STATE" | jq -r '.manual_anchor // ""')" \
  --arg br "$(echo "$STATE" | jq -r '.branch // ""')" \
  --arg dg "$(echo "$STATE" | jq -r '.domain_guess // ""')" \
  --arg rf "$(echo "$STATE" | jq -r '(.active_files_recent // []) | .[:5] | join(", ")')" \
  --arg um "$(echo "$TURN" | jq -r '.user_msg // ""')" \
  --arg as "$(echo "$TURN" | jq -r '.assistant_text // "" | .[:500]')" \
  --arg rt "$(echo "$STATE" | jq -r '(.transition_history // []) | map("turn " + (.turn|tostring) + ": " + .title) | join("\n")')" \
  '{CURRENT_TITLE:$t, MANUAL_ANCHOR:$a, BRANCH:$br, DOMAIN_GUESS:$dg, RECENT_FILES:$rf, USER_MSG:$um, ASSISTANT_SUMMARY:$as, RECENT_TURNS:$rt}')

log_event info llm_call_start "$SESSION_ID" "$(echo "$STATE" | jq -c '{calls_made, overflow_used}')"

LLM_OUTPUT=$(llm_generate_title "$CTX" || echo '{"error":"call_failed"}')
COST=$(echo "$LLM_OUTPUT" | jq -r '._cost_usd // 0')
DURATION=$(echo "$LLM_OUTPUT" | jq -r '._duration_ms // 0')

log_event info llm_call_end "$SESSION_ID" "$(jq -nc --argjson c "$COST" --argjson d "$DURATION" --argjson o "$LLM_OUTPUT" '{cost_usd:$c, duration_ms:$d, output:$o}')"

# --- 8. Validate + write + promote state only on writer success ---
LLM_ERR=$(echo "$LLM_OUTPUT" | jq -r '.error // ""')
if [[ -n "$LLM_ERR" ]]; then
  NEW_FAIL=$(( $(echo "$STATE" | jq -r '.failure_count // 0') + 1 ))
  CB_THR=$(config_get circuit_breaker_threshold)
  STATE=$(echo "$STATE" | jq --argjson n "$NEW_FAIL" --argjson thr "$CB_THR" '
    .failure_count = $n
    | .llm_disabled = ($n >= $thr)
  ')
  if (( NEW_FAIL >= CB_THR )); then
    log_event warn circuit_breaker_tripped "$SESSION_ID" "$(jq -nc --argjson n "$NEW_FAIL" '{failure_count:$n}')"
  fi
  STATE=$(echo "$STATE" | jq --arg s "$CURRENT_SIGNATURE" '.last_processed_signature = $s')
  state_save "$SESSION_ID" "$STATE"
  _HOOK_CLEAN_EXIT=1; exit 0
fi

# Success: reset CB
STATE=$(echo "$STATE" | jq '.failure_count = 0 | .llm_disabled = false')

VALIDATED=$(validate_and_render "$LLM_OUTPUT" "$STATE")
STATUS=$(echo "$VALIDATED" | jq -r '.status')

# Track whether to advance the signature. We advance for all outcomes EXCEPT
# "LLM returned ok but writer failed" — in that case we want the next hook
# to re-evaluate (possibly re-calling LLM) rather than silently stuck.
ADVANCE_SIGNATURE=1

case "$STATUS" in
  ok)
    TITLE=$(echo "$VALIDATED" | jq -r '.rendered_title')
    TS=$(echo "$VALIDATED" | jq -c '.title_struct')
    if writer_append_title "$TRANSCRIPT_PATH" "$TITLE"; then
      # Promote state only after writer confirms
      STATE=$(echo "$STATE" | jq --arg t "$TITLE" --argjson ts "$TS" --argjson tn "$TURN_NUM" '
        (.title_struct // null) as $prev_ts
        | .rendered_title = $t
        | .last_plugin_written_title = $t
        | .title_struct = $ts
        | .accumulated_score = 0
        | (.transition_history // []) as $h
        | .transition_history = (($h + [{turn: $tn, title: $t, reason: (if $prev_ts then "extend" else "first" end)}]) | .[-3:])
      ')
      log_event info title_written "$SESSION_ID" "$(jq -nc --arg t "$TITLE" '{title:$t}')"
    else
      log_event warn title_write_failed "$SESSION_ID" "$(jq -nc --arg t "$TITLE" '{attempted_title:$t}')"
      # Do NOT promote state; do NOT advance signature — next hook will re-evaluate.
      ADVANCE_SIGNATURE=0
    fi
    ;;
  skip_identical)
    STATE=$(echo "$STATE" | jq '.accumulated_score = 0')
    log_event info title_skipped "$SESSION_ID" '{"reason":"identical"}'
    ;;
  *)
    log_event warn title_invalid "$SESSION_ID" "$VALIDATED"
    ;;
esac

if [[ $ADVANCE_SIGNATURE -eq 1 ]]; then
  STATE=$(echo "$STATE" | jq --arg s "$CURRENT_SIGNATURE" '.last_processed_signature = $s')
fi
state_save "$SESSION_ID" "$STATE"
_HOOK_CLEAN_EXIT=1
exit 0
