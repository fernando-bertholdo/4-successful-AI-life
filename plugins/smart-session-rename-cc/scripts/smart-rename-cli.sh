#!/usr/bin/env bash
# smart-rename-cli.sh — skill subcommand dispatcher (v1.5 full)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/config.sh"
source "$SCRIPT_DIR/lib/state.sh"
source "$SCRIPT_DIR/lib/logger.sh"
source "$SCRIPT_DIR/lib/writer.sh"
source "$SCRIPT_DIR/lib/llm.sh"
source "$SCRIPT_DIR/lib/validate.sh"
source "$SCRIPT_DIR/lib/transcript.sh"

_dbg() { [[ -n "${SMART_RENAME_DEBUG:-}" ]] && echo "[debug] $*" >&2 || true; }

_encode_cwd() {
  local p="${1:-$(pwd -P)}"
  # Always resolve symlinks (macOS: /tmp → /private/tmp; Claude Code uses resolved paths)
  if [[ -d "$p" ]]; then
    p="$(cd "$p" && pwd -P)"
  fi
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

with_lock() {
  local sid="$1"; shift
  state_lock "$sid" || { echo "ERROR: could not lock session state"; exit 1; }
  trap "state_unlock $sid" EXIT
  "$@"
}

usage() {
  cat <<EOF
Usage: /smart-rename [args]

  /smart-rename                 Suggest a rename (consumes 1 budget slot, prints suggestion).
  /smart-rename <name>          Set domain anchor to <name> (slug).
  /smart-rename freeze          Pause automatic updates.
  /smart-rename unfreeze        Resume automatic updates.
  /smart-rename force           Force LLM call on next Stop hook.
  /smart-rename explain         Show state, budget, history.
  /smart-rename unanchor        Clear manual anchor.
EOF
}

cmd_freeze() {
  local sid="$1"
  local st; st=$(state_load "$sid")
  state_save "$sid" "$(echo "$st" | jq '.frozen = true | .updated_at = (now | todate)')"
  log_event info freeze_toggled "$sid" '{"frozen":true}'
  echo "Smart rename FROZEN for session $sid"
}

cmd_unfreeze() {
  local sid="$1"
  local st; st=$(state_load "$sid")
  state_save "$sid" "$(echo "$st" | jq '.frozen = false | .updated_at = (now | todate)')"
  log_event info freeze_toggled "$sid" '{"frozen":false}'
  echo "Smart rename UNFROZEN for session $sid"
}

cmd_force() {
  local sid="$1"
  local st; st=$(state_load "$sid")
  state_save "$sid" "$(echo "$st" | jq '.force_next = true | .failure_count = 0 | .llm_disabled = false | .updated_at = (now | todate)')"
  log_event info force_triggered "$sid" '{}'
  echo "Force flag set; will evaluate on next Stop hook."
}

cmd_anchor() {
  local sid="$1" name="$2" transcript="$3"
  local st; st=$(state_load "$sid")

  # Derive transcript from cwd when $CLAUDE_TRANSCRIPT_PATH is empty
  # (same pattern as cmd_suggest — skills don't expose that env var).
  if [[ -z "$transcript" || ! -f "$transcript" ]]; then
    local encoded="$(_encode_cwd)"
    local proj_dir="$HOME/.claude/projects/$encoded"
    transcript="$(ls -t "$proj_dir"/*.jsonl 2>/dev/null | head -1)"
    _dbg "cmd_anchor: transcript derived from cwd=$transcript"
  fi

  # Build rendered_title: domain = anchor; clauses kept from title_struct if present
  local clauses n
  clauses=$(echo "$st" | jq -c '.title_struct.clauses // []')
  n=$(echo "$clauses" | jq 'length')
  local title
  if [[ "$n" -eq 0 ]]; then
    title="$name"
  else
    title="$name: $(echo "$clauses" | jq -r 'join(", ")')"
  fi

  # R4: Write JSONL FIRST; only promote state if the write succeeded.
  if [[ -n "$transcript" && -f "$transcript" ]]; then
    if ! writer_append_title "$transcript" "$title" "$sid"; then
      echo "ERROR: could not append custom-title to transcript; aborting anchor (state unchanged)"
      return 1
    fi
  else
    _dbg "cmd_anchor: no transcript found, state updated but JSONL not written"
  fi

  state_save "$sid" "$(echo "$st" | jq --arg a "$name" --arg t "$title" '
    .manual_anchor = $a
    | .manual_title_override = null
    | .rendered_title = $t
    | (.title_struct // {}) as $ts
    | .title_struct = ($ts + {domain:$a})
    | .last_plugin_written_title = $t
    | .updated_at = (now | todate)
  ')"
  log_event info manual_anchor_set "$sid" "$(jq -nc --arg a "$name" '{anchor:$a}')"
  echo "Anchor set: $name (title: \"$title\")"
}

# R3: unanchor clears BOTH manual_anchor AND manual_title_override so the user
# has a single command to return to fully automatic naming after either a
# /smart-rename <name> or a /rename nativo.
cmd_unanchor() {
  local sid="$1"
  local st; st=$(state_load "$sid")
  state_save "$sid" "$(echo "$st" | jq '
    .manual_anchor = null
    | .manual_title_override = null
    | .updated_at = (now | todate)
  ')"
  log_event info manual_anchor_set "$sid" '{"anchor":null,"override":null}'
  echo "Anchor and title override cleared. Plugin resumes automatic naming on next Stop hook."
}

cmd_explain() {
  local sid="$1"
  config_load
  local st; st=$(state_load "$sid")
  local max_calls=$(config_get max_budget_calls)
  local overflow_slots=$(config_get overflow_manual_slots)
  local first_thr=$(config_get first_call_work_threshold)
  local ongoing_thr=$(config_get ongoing_work_threshold)

  local title=$(echo "$st" | jq -r '.rendered_title // "(not yet named)"')
  local domain=$(echo "$st" | jq -r '.title_struct.domain // "—"')
  local anchor=$(echo "$st" | jq -r '.manual_anchor // "—"')
  local override=$(echo "$st" | jq -r '.manual_title_override // "—"')
  local frozen=$(echo "$st" | jq -r '.frozen // false')
  local force=$(echo "$st" | jq -r '.force_next // false')
  local llm_dis=$(echo "$st" | jq -r '.llm_disabled // false')
  local fc=$(echo "$st" | jq -r '.failure_count // 0')
  local calls=$(echo "$st" | jq -r '.calls_made // 0')
  local overflow=$(echo "$st" | jq -r '.overflow_used // 0')
  local acc=$(echo "$st" | jq -r '.accumulated_score // 0')

  local has_title=$(echo "$st" | jq -r 'if .title_struct then "true" else "false" end')
  local next_thr=$first_thr
  [[ "$has_title" == "true" ]] && next_thr=$ongoing_thr

  cat <<EOF
Título atual: $title
Domínio: $domain (anchor: $anchor, override: $override)
Estado: $([ "$frozen" = "true" ] && echo "congelado" || echo "ativo")$([ "$force" = "true" ] && echo "; force próximo turno" || echo "")

Budget: $calls/$max_calls chamadas usadas, $((max_calls - calls)) restantes · overflow $overflow/$overflow_slots
Circuit breaker: $([ "$llm_dis" = "true" ] && echo "ATIVO (plugin desabilitado)" || echo "OK ($fc falhas consecutivas)")
Work score acumulado: $acc (próximo call em ≥$next_thr)

Últimas transições:
EOF
  echo "$st" | jq -r '
    (.transition_history // [])[] | "  turno \(.turn)  → \(.title)  (\(.reason))"
  ' 2>/dev/null || echo "  (sem histórico ainda)"

  echo ""
  echo "Último evento do log:"
  local log_file="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}/logs/$sid.jsonl"
  if [[ -f "$log_file" ]]; then tail -1 "$log_file"; else echo "  (sem log ainda)"; fi
}

# /smart-rename (no args): suggest. CONSUMES 1 budget slot (A4).
# Mirrors the hook's circuit breaker behavior (N4) and checks validate status (N5).
# Accepts explicit cwd so domain_guess/branch are correct when called from the skill (R5).
cmd_suggest() {
  local sid="$1" transcript="$2" cwd="${3:-$PWD}"
  local st; st=$(state_load "$sid")

  # Derive transcript path from cwd when $CLAUDE_TRANSCRIPT_PATH is empty
  # (Phase 1.3/7.1 lesson: skills don't expose that env var to Bash).
  if [[ -z "$transcript" || ! -r "$transcript" ]]; then
    local encoded="$(_encode_cwd "$cwd")"
    local proj_dir="$HOME/.claude/projects/$encoded"
    transcript="$(ls -t "$proj_dir"/*.jsonl 2>/dev/null | head -1)"
    _dbg "cmd_suggest: transcript derived from cwd=$transcript"
    if [[ -z "$transcript" ]]; then
      echo "ERROR: cannot find transcript for session $sid (tried $proj_dir/*.jsonl)"
      return 1
    fi
  fi

  local calls_made=$(echo "$st" | jq -r '.calls_made // 0')
  local overflow_used=$(echo "$st" | jq -r '.overflow_used // 0')
  local max_calls=$(config_get max_budget_calls)
  local overflow_slots=$(config_get overflow_manual_slots)
  local cb_thr=$(config_get circuit_breaker_threshold)
  local llm_disabled=$(echo "$st" | jq -r '.llm_disabled // false')

  if [[ "$llm_disabled" == "true" ]]; then
    echo "Circuit breaker active (LLM disabled for this session). Use /smart-rename force to reset."
    return 1
  fi

  if [[ "$calls_made" -ge "$max_calls" ]] && [[ "$overflow_used" -ge "$overflow_slots" ]]; then
    echo "Budget and overflow exhausted. Use /smart-rename <name> to anchor manually."
    return 1
  fi

  local prev_files=$(echo "$st" | jq -c '.active_files_recent // []')
  local turn=$(transcript_parse_current_turn "$transcript" "$prev_files" "$cwd")

  local ctx=$(jq -nc \
    --arg t "$(echo "$st" | jq -r '.rendered_title // ""')" \
    --arg a "$(echo "$st" | jq -r '.manual_anchor // ""')" \
    --arg br "$(echo "$turn" | jq -r '.branch // ""')" \
    --arg dg "$(echo "$turn" | jq -r '.domain_guess // ""')" \
    --arg rf "$(echo "$turn" | jq -r '(.all_files_touched // []) | .[:5] | join(", ")')" \
    --arg um "$(echo "$turn" | jq -r '.user_msg // ""')" \
    --arg as "$(echo "$turn" | jq -r '.assistant_text // "" | .[:500]')" \
    --arg rt "" \
    '{CURRENT_TITLE:$t, MANUAL_ANCHOR:$a, BRANCH:$br, DOMAIN_GUESS:$dg, RECENT_FILES:$rf, USER_MSG:$um, ASSISTANT_SUMMARY:$as, RECENT_TURNS:$rt}')

  # Consume budget BEFORE call (consistent with hook behavior). Save immediately so
  # a subsequent crash still records the spend.
  if [[ "$calls_made" -ge "$max_calls" ]]; then
    st=$(echo "$st" | jq '.overflow_used = ((.overflow_used // 0) + 1)')
  else
    st=$(echo "$st" | jq '.calls_made = ((.calls_made // 0) + 1)')
  fi
  state_save "$sid" "$st"

  local out
  out=$(llm_generate_title "$ctx") || true
  # If llm_generate_title returned non-zero, it already echoed {"error":"..."} to stdout.
  # Don't double-wrap — just check if error is present.
  [[ -z "$out" ]] && out='{"error":"call_failed"}'
  local err=$(echo "$out" | jq -r '.error // ""')
  if [[ -n "$err" ]]; then
    # N4: integrate with circuit breaker identically to the hook
    local new_fail=$(($(echo "$st" | jq -r '.failure_count // 0') + 1))
    st=$(echo "$st" | jq --argjson n "$new_fail" --argjson thr "$cb_thr" '
      .failure_count = $n | .llm_disabled = ($n >= $thr)
    ')
    state_save "$sid" "$st"
    log_event warn llm_error "$sid" "$(jq -nc --arg e "$err" --argjson n "$new_fail" '{error:$e, failure_count:$n}')"
    if (( new_fail >= cb_thr )); then
      echo "LLM call failed ($err). Circuit breaker tripped ($new_fail/$cb_thr); use /smart-rename force to reset."
    else
      echo "LLM call failed ($err). Failure count: $new_fail/$cb_thr."
    fi
    return 1
  fi

  # Success resets failure counter (keeps CB behavior consistent across hook/skill)
  st=$(echo "$st" | jq '.failure_count = 0 | .llm_disabled = false')
  state_save "$sid" "$st"

  local validated=$(validate_and_render "$out" "$st")
  local vstatus=$(echo "$validated" | jq -r '.status')

  # N5: treat invalid/error validation results honestly instead of printing "null"
  if [[ "$vstatus" != "ok" && "$vstatus" != "skip_identical" ]]; then
    local verr=$(echo "$validated" | jq -r '.error // "unknown_validation_error"')
    echo "Validation failed: $verr (LLM output was malformed or rejected). No changes applied."
    return 1
  fi

  local title=$(echo "$validated" | jq -r '.rendered_title')
  local sdomain=$(echo "$validated" | jq -r '.title_struct.domain // ""')
  echo "Suggested title: $title"
  echo ""
  echo "To apply as anchor, run:   /smart-rename $sdomain"
  echo "Or accept literally via:   /rename \"$title\"   (native command)"
}

# Dispatcher. Third positional arg to cmd_suggest is optional cwd; the SKILL should
# pass $CLAUDE_PROJECT_DIR when available, else $PWD is used as fallback.
cmd="${1:-}"; shift || true

case "$cmd" in
  "" )
    transcript="${1:-}"
    cwd_arg="${2:-${CLAUDE_PROJECT_DIR:-${PWD:-}}}"
    sid="$(session_id_from_args "$transcript")"
    [[ -z "$sid" ]] && { echo "ERROR: cannot determine session id"; exit 1; }
    with_lock "$sid" cmd_suggest "$sid" "$transcript" "$cwd_arg"
    ;;
  freeze)   sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_freeze "$sid" ;;
  unfreeze) sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_unfreeze "$sid" ;;
  force)    sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_force "$sid" ;;
  unanchor) sid="$(session_id_from_args "${1:-}")"; with_lock "$sid" cmd_unanchor "$sid" ;;
  explain)  sid="$(session_id_from_args "${1:-}")"; cmd_explain "$sid" ;;
  help|-h|--help) usage ;;
  *)
    name="$cmd"
    transcript="${1:-}"
    sid="$(session_id_from_args "$transcript")"
    [[ -z "$sid" ]] && { echo "ERROR: cannot determine session id"; exit 1; }
    with_lock "$sid" cmd_anchor "$sid" "$name" "$transcript"
    ;;
esac
