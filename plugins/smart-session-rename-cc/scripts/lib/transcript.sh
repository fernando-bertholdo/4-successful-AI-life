#!/usr/bin/env bash
# lib/transcript.sh — parse Claude Code JSONL for the current turn.
# Turn = user message + all following assistant blocks until next user.
# Handles both string and array content in user messages (tool_result + text blocks).

# Args: transcript_path, previous_active_files_json, cwd
# Stdout: JSON with turn signals (schema per v1.5 spec §3.5 + file_size for idempotency)
transcript_parse_current_turn() {
  local path="$1" prev_files_json="${2:-[]}" cwd="${3:-}"

  if [[ ! -r "$path" ]]; then
    echo '{"error":"missing_transcript"}'
    return 0
  fi

  local file_size
  file_size=$(wc -c < "$path" | tr -d ' ')

  # CC injects synthetic pseudo-user-messages around slash-commands and platform
  # events (the content is a literal string like "<local-command-caveat>...",
  # "<command-name>/model</command-name>", "<system-reminder>...", etc.). These
  # entries have type:"user" in the JSONL but are not user intent. Treat them as
  # transparent so user_msg, turn count, and the assistant-slice anchor all
  # reference the most recent REAL user prompt.
  local jq_helpers='
    def extract_user_text:
      if type == "string" then .
      elif type == "array" then
        [.[] | select(.type == "text") | .text] | join(" ")
      else "" end;
    def is_real_user_text:
      (gsub("^\\s+|\\s+$"; "")) as $s
      | $s != "" and ($s | test("^<[a-z][a-z0-9-]*>") | not);
    def is_real_user_msg:
      .type == "user"
      and (.message.content | extract_user_text | is_real_user_text);
  '

  local total_turns last_user_msg
  total_turns=$(jq -s "$jq_helpers"'
    [.[] | select(is_real_user_msg)] | length
  ' "$path" 2>/dev/null || echo 0)
  last_user_msg=$(jq -rs "$jq_helpers"'
    [.[] | select(is_real_user_msg) | .message.content | extract_user_text] | last // ""
  ' "$path" 2>/dev/null || echo "")

  local user_word_count
  user_word_count=$(printf '%s' "$last_user_msg" | wc -w | tr -d ' ')

  # All assistant blocks after the last REAL user message (synthetics are skipped
  # when finding the slice anchor — otherwise a trailing synthetic user message
  # would clip the assistant content from this turn down to nothing).
  local assistant_content
  assistant_content=$(jq -s "$jq_helpers"'
    . as $all
    | ([range(0; $all | length) | . as $i | select($all[$i] | is_real_user_msg)] | last // -1) as $lu
    | $all[($lu+1):] | map(select(.type == "assistant"))
  ' "$path" 2>/dev/null || echo '[]')

  local tool_call_count
  tool_call_count=$(echo "$assistant_content" | jq '
    [.[] | .message.content // [] | .[] | select(.type == "tool_use")] | length
  ' 2>/dev/null || echo 0)

  local tool_names
  tool_names=$(echo "$assistant_content" | jq -c '
    [.[] | .message.content // [] | .[] | select(.type == "tool_use") | .name]
  ' 2>/dev/null || echo '[]')

  local all_files
  all_files=$(echo "$assistant_content" | jq -c '
    [.[] | .message.content // [] | .[] | select(.type == "tool_use") | .input.file_path // empty] | unique
  ' 2>/dev/null || echo '[]')

  local new_files
  new_files=$(jq -cn --argjson all "$all_files" --argjson prev "$prev_files_json" '$all - $prev' 2>/dev/null || echo '[]')

  local assistant_text
  assistant_text=$(echo "$assistant_content" | jq -r '
    [.[] | .message.content // [] | .[] | select(.type == "text") | .text] | join(" ")
  ' 2>/dev/null || echo "")

  local assistant_sentence_count
  assistant_sentence_count=$(echo "$assistant_text" | sed 's/```[^`]*```//g' | { grep -oE '[.!?]' || true; } | wc -l | tr -d ' ' || echo 0)

  local domain_guess
  # Try top-level directory dominant (skip generic containers)
  domain_guess=$(echo "$all_files" | jq -r '
    [.[] | split("/")[0] | select(length > 0) | select(. != "src" and . != "tests" and . != "lib" and . != "app" and . != "pkg")]
    | group_by(.) | map({k:.[0], n:length}) | sort_by(-.n) | first.k // empty
  ' 2>/dev/null)
  if [[ -z "$domain_guess" || "$domain_guess" == "null" ]]; then
    # Second-level (e.g., src/auth/...)
    domain_guess=$(echo "$all_files" | jq -r '
      [.[] | split("/") | .[1] // empty | select(. != "")]
      | group_by(.) | map({k:.[0], n:length}) | sort_by(-.n) | first.k // empty
    ' 2>/dev/null)
  fi
  if [[ -z "$domain_guess" || "$domain_guess" == "null" ]]; then
    domain_guess="$(basename "${cwd:-/}")"
  fi

  local branch
  if [[ -n "$cwd" && -d "$cwd" ]]; then
    branch="$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
  else
    branch=""
  fi

  jq -nc \
    --argjson turn "${total_turns:-0}" \
    --arg msg "$last_user_msg" \
    --argjson words "${user_word_count:-0}" \
    --arg atext "$assistant_text" \
    --argjson asent "${assistant_sentence_count:-0}" \
    --argjson tcc "${tool_call_count:-0}" \
    --argjson tnames "$tool_names" \
    --argjson all "$all_files" \
    --argjson nfiles "$new_files" \
    --arg dom "$domain_guess" \
    --arg br "$branch" \
    --argjson fs "${file_size:-0}" \
    '{
      turn_number: $turn,
      user_msg: $msg,
      user_word_count: $words,
      assistant_text: $atext,
      assistant_sentence_count: $asent,
      tool_call_count: $tcc,
      tool_names: $tnames,
      all_files_touched: $all,
      new_files_this_turn: $nfiles,
      domain_guess: $dom,
      branch: $br,
      file_size: $fs
    }'
}
