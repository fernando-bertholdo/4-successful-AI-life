# Session JSONL Format Research

**Date:** 2026-03-24
**Status:** Verified via Claude Code source and GitHub issues

## Custom Title Record Format

When `/rename my-session-name` is executed, Claude Code appends this exact JSON line to the session JSONL:

```json
{"type":"custom-title","customTitle":"my-session-name"}
```

**Key fields:**
- `type`: `"custom-title"` (hyphenated, NOT camelCase)
- `customTitle`: the session name string

## Storage Location

Sessions are stored at: `~/.claude/projects/[encoded-working-directory]/[sessionId].jsonl`

There is also an index file: `~/.claude/projects/[encoded-working-directory]/sessions-index.json`

### sessions-index.json structure:
```json
{
  "version": 1,
  "entries": [
    {
      "sessionId": "uuid",
      "fullPath": "/path/to/session.jsonl",
      "fileMtime": 1768581224044,
      "firstPrompt": "...",
      "messageCount": 13,
      "created": "2026-01-16T16:31:20.540Z",
      "modified": "2026-01-16T16:33:44.039Z",
      "gitBranch": "feature-branch",
      "projectPath": "/home/user/project",
      "isSidechain": false
    }
  ]
}
```

## Known Issue: 64KB Tail Scan

Claude Code scans only the **last 64KB** of each JSONL file for the `customTitle` entry. On long sessions, the custom-title line can get pushed outside this window, causing the session to lose its name in the resume picker.

**Mitigation for our plugin:** Re-append the `custom-title` record on every hook invocation to keep it within the 64KB window.

## References

- [Issue #26240](https://github.com/anthropics/claude-code/issues/26240): Session names lost after resuming
- [Issue #25509](https://github.com/anthropics/claude-code/issues/25509): /rename doesn't persist
- [Issue #33165](https://github.com/anthropics/claude-code/issues/33165): Programmatic session rename API request
