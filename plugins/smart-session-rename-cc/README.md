# claude-code-claude-code-smart-session-rename

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Plugin-purple.svg)

**Auto-name your Claude Code sessions. Stop hunting through `quirky-blue-elephant` and `sharp-gifted-tesla`.**

---

## The Problem

You have 47 sessions named `quirky-blue-elephant`, `sharp-gifted-tesla`, and `mild-curious-darwin`. Good luck finding your auth refactor.

Every time you start a new Claude Code session, it gets assigned a random three-word identifier. Perfect for temporary chats, terrible for actual projects. By the time you've written meaningful code, you've forgotten what the session was supposed to do. You're left digging through history or creating the same session over and over.

---

## The Solution

`claude-code-smart-session-rename` watches your conversations and automatically names your sessions based on what you're actually building. Smart enough to know when your work evolves. Transparent enough to stay out of your way.

- **Auto-names sessions** after your first meaningful message
- **Evolves the name** every 3 messages as your work progresses (e.g., `auth-refactor` → `auth-refactor-with-oauth`)
- **On-demand renaming** via `/smart-rename` when you want to take control

---

## Demo

![Demo](docs/demo.gif)

*In this demo, a developer starts with "Fix login validation bug" and the session is instantly renamed to `fix-login-validation`. Three messages later, after pivoting to OAuth implementation, it becomes `fix-auth-flow`. Seven messages in, after adding unit tests, it's now `fix-auth-flow-with-tests`—all automatic, zero friction.*

---

## Quick Start

Install and done:

```bash
claude plugin install claude-code-smart-session-rename
```

That's it. Zero configuration. The plugin works out of the box.

---

## How It Works

1. **Hooks into your session** — Registers a `Stop` hook that runs asynchronously after each Claude response
2. **Counts your messages** — Tracks user input and decides when to name or rename based on message count thresholds
3. **Generates smart names** — Uses `claude -p` with carefully crafted prompts to generate concise, meaningful titles from conversation context
4. **Writes the title** — Updates your session name using Claude Code's native `custom-title` format
5. **Fails gracefully** — If the LLM call times out or errors, falls back to heuristic naming (word frequency + keyword matching)

The entire process is non-blocking and happens in the background.

---

## Configuration

Customize behavior via environment variables or a config file:

| Variable | Default | Description |
|---|---|---|
| `SMART_RENAME_ENABLED` | `true` | Enable/disable the plugin |
| `SMART_RENAME_UPDATE_INTERVAL` | `3` | Number of messages between auto-rename checks |
| `SMART_RENAME_MIN_WORDS` | `10` | Minimum words in first prompt to trigger naming |
| `SMART_RENAME_MAX_TITLE_WORDS` | `5` | Maximum words allowed in generated title |

Config file location: `~/.claude/plugins/data/claude-code-smart-session-rename/config.json`

Example config:

```json
{
  "enabled": true,
  "updateInterval": 3,
  "minWords": 10,
  "maxTitleWords": 5
}
```

---

## On-Demand Renaming

Want to rename a session right now? Use the `/smart-rename` command:

```
/smart-rename
```

This triggers an immediate rename based on the current conversation, regardless of the message count. Perfect for when your work takes an unexpected turn mid-session.

---

## How Names Evolve

Your session title grows with your work:

| Message | Work | Session Title |
|---|---|---|
| 1 | "Fix the login validation" | `fix-login-validation` |
| 4 | Added OAuth support | `fix-auth-flow` |
| 7 | Added unit tests | `fix-auth-flow-with-tests` |
| 10 | Integrated 2FA | `secure-auth-system` |

Names are designed to be short, GitHub-friendly, and meaningful. Hyphens, no spaces. Always lowercase.

---

## FAQ

**Does this cost money?**

Minimal. The plugin uses Claude Haiku (our fastest, cheapest model) and generates fewer than 200 tokens per naming call. Over a month of heavy use, you're looking at pennies.

**Is it safe? Does it block my session?**

Completely safe. The rename hook runs asynchronously and never blocks your work. If Claude Code is offline or the API is slow, your session continues uninterrupted. Failed naming attempts silently fall back to heuristics.

**Can I disable it or uninstall?**

Yes, on both counts. Set `SMART_RENAME_ENABLED=false` to pause without uninstalling, or:

```bash
claude plugin uninstall claude-code-smart-session-rename
```

Your session will revert to its original random name.

**What if I hate the generated name?**

Use `/smart-rename` to try again, or disable auto-rename and set the title manually. The plugin respects your choices.

---

## Contributing

Found a bug? Have an idea for smarter naming? Contributions are welcome!

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT

---

**Made with ❤️ for Claude Code users who have better things to do than remember session names.**
