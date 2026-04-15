#!/usr/bin/env bash
# lib/validate.sh — validate LLM output and render title.
# Supports manual_title_override (raw text, for /rename nativo detection) separate from
# manual_anchor (domain slug, for /smart-rename <slug>).

# Args: llm_output_json, state_json
# Stdout: {"status":"ok"|"skip_identical"|"invalid"|"error", "rendered_title":"...", "title_struct":{...}}
validate_and_render() {
  local output="$1" state="$2"

  local err
  err=$(echo "$output" | jq -r '.error // ""')
  if [[ -n "$err" ]]; then
    echo "$output" | jq -c --arg e "$err" '{status:"error", error:$e}'
    return 0
  fi

  # Early exit: manual_title_override wins. Render verbatim; title_struct is minimal.
  local override
  override=$(echo "$state" | jq -r '.manual_title_override // ""')
  if [[ -n "$override" && "$override" != "null" ]]; then
    local prev
    prev=$(echo "$state" | jq -r '.rendered_title // ""')
    if [[ "$prev" == "$override" ]]; then
      jq -nc --arg t "$override" '{status:"skip_identical", rendered_title:$t, title_struct:{domain:$t, clauses:[]}}'
    else
      jq -nc --arg t "$override" '{status:"ok", rendered_title:$t, title_struct:{domain:$t, clauses:[]}}'
    fi
    return 0
  fi

  local domain clauses_json clauses_count
  domain=$(echo "$output" | jq -r '.domain // ""')
  clauses_json=$(echo "$output" | jq -c '.clauses // []')
  clauses_count=$(echo "$clauses_json" | jq 'length')

  if [[ -z "$domain" || "$domain" == "null" ]]; then
    echo '{"status":"invalid","error":"empty_domain"}'
    return 0
  fi
  if [[ "$clauses_count" -eq 0 ]]; then
    echo '{"status":"invalid","error":"empty_clauses"}'
    return 0
  fi

  local max_clauses max_domain_chars
  max_clauses=$(config_get max_clauses)
  max_domain_chars=$(config_get max_domain_chars)
  domain="${domain:0:$max_domain_chars}"

  local manual_anchor
  manual_anchor=$(echo "$state" | jq -r '.manual_anchor // ""')
  if [[ -n "$manual_anchor" && "$manual_anchor" != "null" ]]; then
    domain="$manual_anchor"
  fi

  local deduped
  deduped=$(echo "$clauses_json" | jq -c --argjson max "$max_clauses" '
    [.[]
      | gsub("^\\s+|\\s+$"; "")
      | gsub("\\s+"; " ")
      | select(length > 0)
    ]
    | reduce .[] as $c (
        {seen: {}, out: []};
        ($c | ascii_downcase) as $k
        | if .seen[$k] then .
          else .seen[$k] = true | .out += [$c]
          end
      )
    | .out[:$max]
  ')

  local deduped_count
  deduped_count=$(echo "$deduped" | jq 'length')
  if [[ "$deduped_count" -eq 0 ]]; then
    echo '{"status":"invalid","error":"all_clauses_empty_after_dedupe"}'
    return 0
  fi

  local joined rendered
  joined=$(echo "$deduped" | jq -r 'join(", ")')
  rendered="$domain: $joined"

  local prev
  prev=$(echo "$state" | jq -r '.rendered_title // ""')
  if [[ "$prev" == "$rendered" ]]; then
    jq -nc --arg t "$rendered" --arg d "$domain" --argjson cl "$deduped" \
      '{status:"skip_identical", rendered_title:$t, title_struct:{domain:$d, clauses:$cl}}'
    return 0
  fi

  jq -nc --arg t "$rendered" --arg d "$domain" --argjson cl "$deduped" \
    '{status:"ok", rendered_title:$t, title_struct:{domain:$d, clauses:$cl}}'
}
