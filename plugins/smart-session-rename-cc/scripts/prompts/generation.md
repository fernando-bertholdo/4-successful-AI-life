You are generating a concise title for an ongoing Claude Code session.

CURRENT TITLE: ${CURRENT_TITLE}
MANUAL ANCHOR: ${MANUAL_ANCHOR}
CURRENT BRANCH: ${BRANCH}
DOMAIN GUESS: ${DOMAIN_GUESS}
RECENT FILES: ${RECENT_FILES}

USER MESSAGE (this turn):
${USER_MSG}

ASSISTANT SUMMARY (this turn, truncated):
${ASSISTANT_SUMMARY}

RECENT CONTEXT (last 3 turns):
${RECENT_TURNS}

RULES:
- Produce {domain, clauses[]} matching the JSON schema provided via --json-schema.
- `domain`: short slug (1-3 words) naming the subject area (e.g., "auth", "deploy-pipeline").
- If MANUAL ANCHOR is set and non-empty, use it exactly as `domain`.
- `clauses`: 1 to 5 items, each `[verb] [concrete entity]` (e.g., "fix jwt expiry", "add tests").
  - Avoid generic jargon ("implementation", "enhancement", "optimization").
  - Prefer active verbs. Entities should be concrete (file, module, behavior).
- If nothing substantial changed versus CURRENT TITLE, return the same structure — the plugin deduplicates identical renderings without re-writing.
- Keep the domain stable across turns unless the subject clearly changed.
