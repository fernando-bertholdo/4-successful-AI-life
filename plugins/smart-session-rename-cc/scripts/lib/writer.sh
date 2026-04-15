#!/usr/bin/env bash
# lib/writer.sh — append custom-title records to session JSONL.
# Returns non-zero on failure so callers can avoid promoting state prematurely.

writer_append_title() {
  local transcript="$1" title="$2"
  [[ ! -f "$transcript" ]] && return 1
  [[ ! -w "$transcript" ]] && return 1
  jq -nc --arg t "$title" '{type:"custom-title", customTitle:$t}' >> "$transcript"
}

writer_get_last_custom_title() {
  local transcript="$1"
  [[ ! -r "$transcript" ]] && { echo ""; return 0; }
  jq -rs '[.[] | select(.type == "custom-title")] | last.customTitle // empty' "$transcript" 2>/dev/null
}
