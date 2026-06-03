#!/usr/bin/env bash
# lib/writer.sh — append custom-title records to session JSONL.
# Returns non-zero on failure so callers can avoid promoting state prematurely.

writer_append_title() {
  local transcript="$1" title="$2" session_id="${3:-}"
  [[ ! -f "$transcript" ]] && return 1
  [[ ! -w "$transcript" ]] && return 1
  if [[ -n "$session_id" ]]; then
    jq -nc --arg t "$title" --arg s "$session_id" \
      '{type:"custom-title", customTitle:$t, sessionId:$s}' >> "$transcript"
  else
    jq -nc --arg t "$title" '{type:"custom-title", customTitle:$t}' >> "$transcript"
  fi
}

writer_get_last_custom_title() {
  local transcript="$1"
  [[ ! -r "$transcript" ]] && { echo ""; return 0; }
  jq -rs '[.[] | select(.type == "custom-title")] | last.customTitle // empty' "$transcript" 2>/dev/null
}

# True (rc 0) when the title looks like a CC-generated auto-title rather than a real
# /rename nativo. Claude Code names sessions from the first user message in the JSONL,
# and synthetic pseudo-user messages (slash-command wrappers, system reminders, task
# notifications) leak through as titles like "<local-command-caveat>... (Branch 2)".
# Without this guard, rename-hook.sh promotes such titles to manual_title_override and
# bypasses every validation step, freezing the session under a junk name.
writer_is_spurious_auto_title() {
  local t="$1"
  [[ -z "$t" ]] && return 1
  [[ "$t" == "<"* ]] && return 0
  (( ${#t} > 200 )) && return 0
  return 1
}
