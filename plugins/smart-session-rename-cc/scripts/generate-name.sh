#!/usr/bin/env bash
# generate-name.sh — Name generation via claude -p and fallback heuristics
# Sourced by rename-hook.sh. Requires utils.sh to be sourced first.

# Extract the first user message from a transcript JSONL
# Claude Code JSONL format: {"type":"user", "message":{"role":"user","content":"..."}}
# Filter out system/command messages that start with '<' (after trimming whitespace)
extract_first_user_prompt() {
  local transcript="$1"
  jq -r 'select(.type == "user") | .message.content // empty' "$transcript" \
    | sed 's/^[[:space:]]*//' \
    | grep -v '^<' \
    | grep -v '^$' \
    | head -1
}

# Extract recent user messages (last N) from transcript
extract_recent_context() {
  local transcript="$1"
  local count="${2:-2}"
  jq -r 'select(.type == "user") | .message.content // empty' "$transcript" \
    | sed 's/^[[:space:]]*//' \
    | grep -v '^<' \
    | grep -v '^$' \
    | tail -"$count"
}

# Count user messages in transcript (excluding commands/system)
count_user_messages() {
  local transcript="$1"
  jq -r 'select(.type == "user") | .message.content // empty' "$transcript" \
    | sed 's/^[[:space:]]*//' \
    | grep -cv '^<' \
    || echo "0"
}

# Validate and clean LLM output into a valid session name
parse_generated_name() {
  local raw="$1"
  local cleaned
  cleaned=$(echo "$raw" | tr -d '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  # Strip surrounding quotes
  cleaned=$(echo "$cleaned" | sed "s/^['\"]//;s/['\"]$//")
  if validate_name "$cleaned"; then
    echo "$cleaned"
  else
    echo ""
  fi
}

# Fallback: generate a name heuristically from the first prompt
fallback_name() {
  local prompt="$1"
  echo "$prompt" \
    | tr '[:upper:]' '[:lower:]' \
    | tr -cs 'a-z0-9 ' ' ' \
    | awk '{for(i=1;i<=NF && i<=4;i++) printf "%s%s",$i,(i<4 && i<NF?"-":""); print ""}' \
    | sed 's/-$//'
}

# Generate initial session name using claude -p
generate_initial_name() {
  local first_prompt="$1"
  local cwd="$2"

  local prompt
  prompt="You are naming a Claude Code session. Based on the user's first message, generate a concise 2-4 word kebab-case session name that captures the primary intent.

User's first message:
\"\"\"
${first_prompt}
\"\"\"

Working directory: ${cwd}

Rules:
- Use kebab-case (e.g., fix-login-bug, refactor-auth-module)
- 2-4 words maximum
- Focus on the ACTION and TARGET (what + where)
- Output ONLY the name, nothing else
- No quotes, no explanation, no newlines
- Example valid output: fix-login-validation"

  local raw_name
  raw_name=$(claude -p "$prompt" 2>/dev/null) || raw_name=""

  local name
  name=$(parse_generated_name "$raw_name")

  if [[ -n "$name" ]]; then
    echo "$name"
  else
    fallback_name "$first_prompt"
  fi
}

# Generate updated session name using claude -p
generate_updated_name() {
  local current_title="$1"
  local original_title="$2"
  local recent_context="$3"

  local prompt
  prompt="You are updating a Claude Code session name. The session has evolved. Derive a new name from the current one that reflects the broader scope.

Current title: ${current_title}
Original title: ${original_title}

Recent conversation context (last 2-3 turns):
\"\"\"
${recent_context}
\"\"\"

Rules:
- Evolve from the current title, don't create something unrelated
- Use kebab-case, 2-5 words maximum
- If the work hasn't meaningfully changed scope, output the current title unchanged
- Output ONLY the name, nothing else
- No quotes, no explanation, no newlines"

  local raw_name
  raw_name=$(claude -p "$prompt" 2>/dev/null) || raw_name=""

  local name
  name=$(parse_generated_name "$raw_name")

  if [[ -n "$name" ]]; then
    echo "$name"
  else
    echo "$current_title"
  fi
}
