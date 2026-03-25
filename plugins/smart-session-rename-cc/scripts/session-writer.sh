#!/usr/bin/env bash
# session-writer.sh — Writes session title to JSONL session files
# Sourced by rename-hook.sh. Requires utils.sh to be sourced first.
#
# VERIFIED FORMAT: Claude Code uses {"type":"custom-title","customTitle":"..."}
# See docs/session-format-research.md for details.

# Write a customTitle record to the session JSONL file.
#
# Args:
#   $1 - session_file: path to the session JSONL file
#   $2 - title: the session name to write
#   $3 - session_id: for logging purposes
#
# Returns: 0 on success, 1 on failure
write_session_title() {
  local session_file="$1"
  local title="$2"
  local session_id="$3"

  # Verify file exists
  if [[ ! -f "$session_file" ]]; then
    log_error "$session_id" "Session file not found: $session_file"
    return 1
  fi

  # Verify file is writable
  if [[ ! -w "$session_file" ]]; then
    log_error "$session_id" "Session file not writable: $session_file"
    return 1
  fi

  # Build the custom-title record (matches Claude Code's /rename format)
  local record
  record=$(jq -cn \
    --arg type "custom-title" \
    --arg title "$title" \
    '{type: $type, customTitle: $title}')

  # Append to session file
  if echo "$record" >> "$session_file"; then
    log_info "$session_id" "Title written: '$title' -> $session_file"
    return 0
  else
    log_error "$session_id" "Failed to write title to: $session_file"
    return 1
  fi
}
