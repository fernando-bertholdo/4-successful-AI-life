# multica-ops

**Operate a [Multica](https://multica.ai) board from Claude Code — without guessing ids and without dispatching agent runs by accident.**

Version `0.1.0` · 1 skill · native plugin

---

## What it is

Multica is an agentic project-management platform: issues on a board, agents that pick them up, and a local daemon that runs them. The desktop app ships a CLI that is not on `PATH`, whose output shapes are not what you would guess, and whose most common commands have side effects a session should not trigger on its own.

This plugin is the operating manual a session needs before it touches a board:

- **Where the CLI is** and why `command -v multica` finds nothing.
- **Discovery instead of hardcoding** — profiles from `~/.multica/profiles`, workspaces from `workspace list`, everything else from `agent`/`project`/`skill list`. No UUID is ever typed from memory.
- **Two routes**: direct from Claude Code on the machine with the desktop app, and through the desktop bridge from a Cowork or claude.ai session — including the quoting, exit-code and cleanup traps of that second route.
- **Safe defaults**: `--no-start` on every status change, no comments on unscoped issues, promotion and deployment left to a human, and a trace on every act performed with a human's profile.
- **Measured gotchas** — the JSON shapes that are not arrays, the flag that is positional, the 100-item page cap, and the zsh word-splitting bugs that have quietly produced malformed issues.
- **What the platform will not do** — workspace isolation, artifacts disabled inside agent tasks, and the absence of any MCP surface.

## Install

```
/plugin marketplace add fernando-bertholdo/4-successful-AI-life
/plugin install multica-ops@4-successful-ai-life
/reload-plugins
```

## Use

The skill is model-invoked: ask about a board, an issue, or a Multica agent and it loads. To pull it in explicitly:

```
/multica-ops:board
```

## Configuration

Two optional environment variables, both read by the skill:

| Variable | What it does |
|---|---|
| `MULTICA_BIN` | Path to the `multica` binary. Defaults to the macOS desktop-app location. |
| `MULTICA_PROFILE` | Profile name. The available names are the directories under `~/.multica/profiles`. |
| `MULTICA_PLAYBOOK` | Path to the repository that versions your Multica configuration, if you keep one. When set, that repo — its manifests, drift check and deploy script — is the authority on ids and procedure, and the skill defers to it. |

Nothing about a specific board ships in this plugin: no workspace ids, no project names, no machine paths. The skill discovers them at runtime, so it works on any Multica installation.

## Compatibility

Measured against **Multica CLI v0.4.42**. The CLI ships changes almost daily; the skill instructs you to record `multica --version` next to any claim about the surface, and command shapes noted here may drift. Issues and corrections welcome on the [tracker](https://github.com/fernando-bertholdo/4-successful-AI-life/issues).

## License

MIT — see [LICENSE](./LICENSE).
