# Smart Session Rename — Design Spec

**Date:** 2026-03-24
**Author:** Fernando + Claude
**Status:** Approved

---

## Problem Statement

Claude Code sessions are identified by auto-generated names — random strings of letters and numbers, or whimsical adjective-noun pairs (e.g., "sharp-gifted-tesla") that don't communicate what the session is about. When a user has dozens of sessions, finding the right one becomes a frustrating guessing game.

There is no built-in mechanism to automatically name sessions based on their content. The only option is manually typing `/rename <name>` — which most users forget or find tedious.

## Solution

A Claude Code **plugin** called `smart-session-rename` that:

1. **Automatically names sessions** after the first meaningful interaction
2. **Evolves the name** every N messages (default: 3) to reflect how the work progresses
3. **Derives updates from the original title** to maintain coherence (not random new names each time)
4. **Provides an on-demand command** (`/smart-rename`) for manual trigger

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│  Claude Code Session                        │
│                                             │
│  User prompt → Claude responds → Hook fires │
│                       │                     │
│                       ▼                     │
│              ┌────────────────┐             │
│              │  Stop Hook     │             │
│              │  (async)       │             │
│              └───────┬────────┘             │
│                      │                      │
│                      ▼                      │
│         ┌─────────────────────┐             │
│         │  rename-hook.sh     │             │
│         │                     │             │
│         │  1. Read stdin JSON │             │
│         │  2. Count messages  │             │
│         │  3. Check threshold │             │
│         │  4. Generate name   │             │
│         │  5. Write to session│             │
│         └─────────────────────┘             │
│                      │                      │
│              ┌───────┴───────┐              │
│              ▼               ▼              │
│     ┌──────────────┐ ┌────────────┐        │
│     │ claude -p    │ │ session    │        │
│     │ (name gen)   │ │ JSONL file │        │
│     └──────────────┘ └────────────┘        │
└─────────────────────────────────────────────┘
```

## Components

### 1. Plugin Manifest (`.claude-plugin/plugin.json`)

```json
{
  "name": "smart-session-rename",
  "version": "1.0.0",
  "description": "Automatically names and renames Claude Code sessions based on conversation content",
  "author": {
    "name": "Fernando Bertholdo",
    "url": "https://github.com/fe-bertholdo"
  },
  "repository": "https://github.com/fe-bertholdo/smart-session-rename",
  "license": "MIT",
  "keywords": ["session", "rename", "productivity", "hooks"],
  "hooks": "./hooks/hooks.json",
  "skills": "./skills/"
}
```

### 2. Hook Configuration (`hooks/hooks.json`)

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/rename-hook.sh",
            "timeout": 30,
            "async": true
          }
        ]
      }
    ]
  }
}
```

**Key decisions:**
- `async: true` — renaming happens in background, never blocks the session
- `timeout: 30` — generous but bounded; the `claude -p` call is the bottleneck
- No matcher — fires on every `Stop` event; the script itself decides whether to act

### 3. Core Script (`scripts/rename-hook.sh`)

**Responsibilities:**
- Parse hook input JSON from stdin
- Read and count messages in the transcript
- Decide whether to rename (based on message count thresholds)
- Generate name via `claude -p` with a compact prompt
- Write the name to the session file

**Input (from stdin):**
```json
{
  "session_id": "abc-123-def",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/home/user/project",
  "hook_event_name": "Stop"
}
```

**State management:**
State is stored in `${CLAUDE_PLUGIN_DATA}/state/{session_id}.json`:
```json
{
  "message_count": 5,
  "current_title": "fix-auth-middleware",
  "original_title": "fix-auth-middleware",
  "last_renamed_at_count": 3,
  "created_at": "2026-03-24T10:30:00Z"
}
```

### 4. Name Generation (`scripts/generate-name.sh`)

**Strategy:**

For **initial naming** (first meaningful interaction):
- Extract the user's first prompt from the transcript
- If prompt is too short (<10 words, e.g., "hi", "test"), skip and wait for more context
- Call `claude -p` with a focused prompt asking for a 2-4 word kebab-case name

For **updates** (every N messages):
- Extract: original title, current title, last 2-3 conversation turns
- Call `claude -p` asking to derive a new name from the current one
- The prompt emphasizes: evolve, don't replace; keep coherent with the original

**Prompt template (initial):**
```
You are naming a Claude Code session. Based on the user's first message,
generate a concise 2-4 word kebab-case session name that captures the
primary intent.

User's first message:
"""
{first_prompt}
"""

Working directory: {cwd}

Rules:
- Use kebab-case (e.g., fix-login-bug, refactor-auth-module)
- 2-4 words maximum
- Focus on the ACTION and TARGET (what + where)
- Output ONLY the name, nothing else
- No quotes, no explanation, no newlines
- Example valid output: fix-login-validation
```

**Output parsing:**
- Strip leading/trailing whitespace and newlines
- Reject if output contains spaces (should be kebab-case), newlines, or is empty
- Reject if more than 6 words (hyphen-separated)
- On rejection: fall back to truncating the first prompt to 4 words in kebab-case

**Prompt template (update):**
```
You are updating a Claude Code session name. The session has evolved.
Derive a new name from the current one that reflects the broader scope.

Current title: {current_title}
Original title: {original_title}

Recent conversation context (last 2-3 turns):
"""
{recent_context}
"""

Rules:
- Evolve from the current title, don't create something unrelated
- Use kebab-case, 2-5 words maximum
- If the work hasn't meaningfully changed scope, output the current title unchanged
- Output ONLY the name, nothing else
```

### 5. Session File Writing

**Mechanism:** Append a title record to the session JSONL file.

Based on research, session files at `~/.claude/projects/{hash}/sessions/{id}.jsonl` store metadata including `customTitle`. The script will:

1. **Path resolution algorithm:**
   - The hook input provides `transcript_path` (e.g., `/home/user/.claude/projects/{hash}/sessions/{id}.jsonl`)
   - The script uses `transcript_path` directly — no scanning needed
   - If `transcript_path` is unavailable, fall back to: scan `~/.claude/projects/*/sessions/` for a file matching `{session_id}.jsonl`
   - Cache resolved paths in the state file to avoid repeated lookups

2. **Title record format:**
   - Append a JSON line: `{"type":"summary","title":"<name>","timestamp":"<ISO-8601>"}`
   - This format needs empirical verification during implementation (see Risks section)
   - The implementation MUST first inspect an existing session file with a known `/rename` title to reverse-engineer the exact record format

3. **Re-append strategy:**
   - The session picker may scan only the tail of JSONL files
   - The periodic update mechanism (every N messages) naturally re-appends the title near the end
   - As a safety net, on every hook run, if the title hasn't changed, re-append the current title anyway

**Fallback chain:**
1. Write to session JSONL → if fails:
2. Log error to `${CLAUDE_PLUGIN_DATA}/logs/{session_id}.log` → continue silently
3. Never disrupt the active session under any circumstances

**Failure visibility:** Users can check `${CLAUDE_PLUGIN_DATA}/logs/` or invoke `/smart-rename status` to see recent activity and any errors.

### 6. On-Demand Skill (`skills/smart-rename/SKILL.md`)

A skill that the user can invoke with `/smart-rename` for manual triggering.

**Behavior:**
1. Read the current session transcript
2. Generate a concise, descriptive name based on all conversation context
3. Present the suggested name to the user
4. Execute `/rename <suggested-name>` upon confirmation

This skill works through Claude's native conversation flow, so it can use `/rename` directly (unlike the hook which must write to files).

## Decision Logic Flowchart

```
Stop hook fires
       │
       ▼
  Read stdin JSON
  (session_id, transcript_path)
       │
       ▼
  Load state from plugin data
  (or create if first run)
       │
       ▼
  Count user messages in transcript
       │
       ▼
  ┌─────────────────────────┐
  │ Is this the first run   │──yes──► First prompt > 10 words?
  │ for this session?       │              │
  └─────────────────────────┘           yes │ no
       │ no                                │   │
       ▼                                   ▼   ▼
  Messages since last     Generate     Wait for
  rename >= N (default 3)?  initial     next Stop
       │                    title
    yes│ no                    │
       │   │                   ▼
       ▼   ▼           Write to session
  Generate  Exit        Save state
  updated   silently    Exit
  title
       │
       ▼
  Has scope actually
  changed?
       │
    yes│ no
       │   │
       ▼   ▼
  Write   Exit
  to      silently
  session
```

## Configuration

Users can configure behavior via environment variables or a config file at `${CLAUDE_PLUGIN_DATA}/config.json`.

**Precedence** (highest to lowest):
1. Environment variables (e.g., `SMART_RENAME_UPDATE_INTERVAL=5`)
2. Config file (`${CLAUDE_PLUGIN_DATA}/config.json`)
3. Hardcoded defaults

**Environment variables:**
| Variable | Default | Description |
|---|---|---|
| `SMART_RENAME_ENABLED` | `true` | Enable/disable auto-rename |
| `SMART_RENAME_UPDATE_INTERVAL` | `3` | Messages between title updates |
| `SMART_RENAME_MIN_WORDS` | `10` | Min words in first prompt to trigger initial naming |
| `SMART_RENAME_MAX_TITLE_WORDS` | `5` | Max words in generated title |

**Config file example:**
```json
{
  "enabled": true,
  "update_interval": 3,
  "min_first_prompt_words": 10,
  "max_title_words": 5
}
```

Defaults are sensible — zero configuration required for basic usage.

## Concurrency and State Safety

**File locking:** The state file (`${CLAUDE_PLUGIN_DATA}/state/{session_id}.json`) uses advisory file locking via `flock` to prevent concurrent writes from multiple hook invocations. If the lock cannot be acquired within 2 seconds, the hook exits silently.

**Atomic writes:** State updates use write-to-temp-then-rename pattern to avoid partial writes on crash.

## Interaction Between Hook and Skill

**Priority model:**
- If a user manually renames via `/rename` or `/smart-rename`, the hook detects this by comparing the current session title with its stored `current_title`. If they differ, the hook treats the manual name as authoritative and updates its state accordingly.
- The hook never overwrites a name that was set more recently by the user.
- The skill `/smart-rename` always takes precedence — it updates both the session and the hook's state file.

## Message Counting Definition

A "user message" is defined as a distinct user turn in the transcript JSONL — specifically, entries with `role: "user"` and `type: "human"`. This excludes:
- System messages and metadata entries
- Tool calls and tool results
- Claude's responses
- `/rename` and other slash commands

## Repository Structure (for open-source distribution)

```
smart-session-rename/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   └── hooks.json
├── scripts/
│   ├── rename-hook.sh          # Main hook entry point
│   ├── generate-name.sh        # Name generation via claude -p
│   ├── session-writer.sh       # Writes title to session JSONL
│   └── utils.sh                # Shared utilities (JSON parsing, etc.)
├── skills/
│   └── smart-rename/
│       └── SKILL.md
├── config/
│   └── default-config.json
├── docs/
│   ├── how-it-works.md
│   ├── configuration.md
│   └── specs/
│       └── 2026-03-24-smart-session-rename-design.md
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── CONTRIBUTING.md
│   └── workflows/
│       └── ci.yml
├── tests/
│   ├── test-rename-hook.sh
│   ├── test-generate-name.sh
│   └── fixtures/
│       ├── sample-transcript.jsonl
│       └── sample-hook-input.json
├── README.md
├── CHANGELOG.md
└── LICENSE
```

## GitHub Appeal Strategy

To maximize stars and adoption:

1. **README.md** — Hero section with animated GIF showing before/after, one-line install command, badges (version, license, stars, "works with Claude Code")
2. **Problem framing** — "You have 47 sessions named `quirky-blue-elephant`. Good luck finding your auth refactor."
3. **Zero-config install** — Single `/plugin install` command, works immediately
4. **Demo GIF** — Record a terminal session showing: start session → work on something → session auto-renames → list sessions with meaningful names
5. **Social proof** — "Compatible with Claude Code v1.x+" badge
6. **Contributing guide** — Lower the barrier for PRs

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Session JSONL format changes | Rename silently fails | **Implementation step 0:** reverse-engineer format from a real session with `/rename`; graceful fallback; log errors; async so no session disruption |
| `claude -p` call is slow/fails | Name generation delayed | async execution + timeout; skip silently on failure |
| Token cost from `claude -p` calls | Small ongoing cost | Uses default Haiku model (cheapest); prompt is <200 tokens |
| Long sessions lose title (64KB tail scan) | Title disappears from picker | Re-append on every update cycle; natural fix |
| User has no Claude API access configured | Plugin doesn't work | Detect and log helpful error; suggest fallback heuristic mode |

## Future Enhancements (v2+)

- Configurable naming templates (`{emoji} {branch}: {description}`)
- Session tagging / categorization beyond just names
- Integration with git branch names for context
- Analytics dashboard showing session activity
- Support for team-shared naming conventions
