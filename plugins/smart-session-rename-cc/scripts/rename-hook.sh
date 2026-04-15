#!/usr/bin/env bash
# rename-hook.sh — Main hook entry point for smart session renaming.
# Called by Claude Code's Stop hook. Reads JSON from stdin.
#
# Flow:
# 1. Read hook input (session_id, transcript_path, cwd)
# 2. Load config and state
# 3. Count user messages
# 4. Decide: initial name, update, or skip
# 5. Generate name (LLM or fallback)
# 6. Write to session file
# 7. Save state
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
source "$SCRIPT_DIR/generate-name.sh"
source "$SCRIPT_DIR/session-writer.sh"

# --- Read hook input from stdin ---
HOOK_INPUT=$(cat)
SESSION_ID=$(echo "$HOOK_INPUT" | jq -r '.session_id // empty')
TRANSCRIPT_PATH=$(echo "$HOOK_INPUT" | jq -r '.transcript_path // empty')
CWD=$(echo "$HOOK_INPUT" | jq -r '.cwd // empty')

# Check required dependencies
for cmd in jq claude; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "smart-session-rename: missing dependency '$cmd'" >&2
    exit 0
  fi
done

# Bail if missing session_id
if [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

# Path resolution: use transcript_path if available, otherwise scan
if [[ -z "$TRANSCRIPT_PATH" || ! -f "$TRANSCRIPT_PATH" ]]; then
  TRANSCRIPT_PATH=$(find ~/.claude/projects -name "${SESSION_ID}.jsonl" -type f 2>/dev/null | head -1)
  if [[ -z "$TRANSCRIPT_PATH" ]]; then
    log_error "$SESSION_ID" "Could not resolve transcript path"
    exit 0
  fi
fi

# --- Load config ---
load_config

# Check if disabled
if [[ "$CFG_ENABLED" != "true" ]]; then
  exit 0
fi

# --- Verify transcript exists ---
if [[ ! -f "$TRANSCRIPT_PATH" ]]; then
  log_error "$SESSION_ID" "Transcript not found: $TRANSCRIPT_PATH"
  exit 0
fi

# --- State management with portable locking ---
STATE_DIR="${CLAUDE_PLUGIN_DATA:-/tmp/smart-session-rename}/state"
mkdir -p "$STATE_DIR"
STATE_FILE="$STATE_DIR/$SESSION_ID.json"
LOCK_DIR="$STATE_FILE.lockdir"

# Portable lock using mkdir (atomic on all POSIX systems)
acquire_lock() {
  local max_wait=2
  local waited=0
  while ! mkdir "$LOCK_DIR" 2>/dev/null; do
    if [[ $waited -ge $max_wait ]]; then
      return 1
    fi
    sleep 0.5
    waited=$((waited + 1))
  done
  # Ensure lock is released on exit
  trap 'rm -rf "$LOCK_DIR"' EXIT
  return 0
}

if ! acquire_lock; then
  log_info "$SESSION_ID" "Could not acquire lock, skipping"
  exit 0
fi

# Load existing state (handle corrupted state gracefully)
STATE=$(read_state "$STATE_FILE")
if ! echo "$STATE" | jq -e '.' > /dev/null 2>&1; then
  STATE='{}'
  log_info "$SESSION_ID" "Reset corrupted state"
fi
CURRENT_TITLE=$(echo "$STATE" | jq -r '.current_title // empty')
ORIGINAL_TITLE=$(echo "$STATE" | jq -r '.original_title // empty')
LAST_RENAMED_AT=$(echo "$STATE" | jq -r '.last_renamed_at_count // "0"')

# --- Count current messages ---
MSG_COUNT=$(count_user_messages "$TRANSCRIPT_PATH")

# --- Decision logic ---

if [[ -z "$CURRENT_TITLE" ]]; then
  # FIRST RUN: no title yet
  FIRST_PROMPT=$(extract_first_user_prompt "$TRANSCRIPT_PATH")
  WORD_COUNT=$(count_words "$FIRST_PROMPT")

  if [[ "$WORD_COUNT" -lt "$CFG_MIN_FIRST_PROMPT_WORDS" ]]; then
    # Prompt too short — save state but don't name yet
    NEW_STATE=$(jq -cn \
      --arg mc "$MSG_COUNT" \
      --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      '{message_count: ($mc | tonumber), created_at: $ts}')
    write_state "$STATE_FILE" "$NEW_STATE"
    exit 0
  fi

  # Generate initial name
  log_info "$SESSION_ID" "Generating initial name (msg_count=$MSG_COUNT)"
  NEW_TITLE=$(generate_initial_name "$FIRST_PROMPT" "$CWD")

  if [[ -n "$NEW_TITLE" ]]; then
    write_session_title "$TRANSCRIPT_PATH" "$NEW_TITLE" "$SESSION_ID" || true
    NEW_STATE=$(jq -cn \
      --arg ct "$NEW_TITLE" \
      --arg ot "$NEW_TITLE" \
      --arg mc "$MSG_COUNT" \
      --arg lr "$MSG_COUNT" \
      --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      '{current_title: $ct, original_title: $ot, message_count: ($mc | tonumber), last_renamed_at_count: ($lr | tonumber), created_at: $ts}')
    write_state "$STATE_FILE" "$NEW_STATE"
    log_info "$SESSION_ID" "Initial title: '$NEW_TITLE'"
  fi

else
  # SUBSEQUENT RUN: check if update is needed
  MSGS_SINCE_LAST=$((MSG_COUNT - LAST_RENAMED_AT))

  if [[ "$MSGS_SINCE_LAST" -ge "$CFG_UPDATE_INTERVAL" ]]; then
    # Time to update
    log_info "$SESSION_ID" "Updating title (msgs_since_last=$MSGS_SINCE_LAST)"
    RECENT_CONTEXT=$(extract_recent_context "$TRANSCRIPT_PATH" 3)
    NEW_TITLE=$(generate_updated_name "$CURRENT_TITLE" "$ORIGINAL_TITLE" "$RECENT_CONTEXT")

    if [[ -n "$NEW_TITLE" ]]; then
      write_session_title "$TRANSCRIPT_PATH" "$NEW_TITLE" "$SESSION_ID" || true
      NEW_STATE=$(jq -cn \
        --arg ct "$NEW_TITLE" \
        --arg ot "$ORIGINAL_TITLE" \
        --arg mc "$MSG_COUNT" \
        --arg lr "$MSG_COUNT" \
        --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{current_title: $ct, original_title: $ot, message_count: ($mc | tonumber), last_renamed_at_count: ($lr | tonumber), created_at: $ts}')
      write_state "$STATE_FILE" "$NEW_STATE"
      log_info "$SESSION_ID" "Updated title: '$CURRENT_TITLE' -> '$NEW_TITLE'"
    fi
  else
    # Not time to update — re-append current title and update message count
    write_session_title "$TRANSCRIPT_PATH" "$CURRENT_TITLE" "$SESSION_ID" || true
    NEW_STATE=$(echo "$STATE" | jq --arg mc "$MSG_COUNT" '.message_count = ($mc | tonumber)')
    write_state "$STATE_FILE" "$NEW_STATE"
  fi
fi
