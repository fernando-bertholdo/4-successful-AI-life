# multica-ops

**The layer around [Multica](https://multica.ai)'s official CLI skill — the environment, the shapes, the limits, and the governance.**

Version `0.2.0` · 1 skill · native plugin

---

## Install the official skill first

Multica publishes the canonical CLI skill at [`multica-ai/multica-cli`](https://github.com/multica-ai/multica-cli), and it is genuinely well maintained: a linter checks every documented command and flag against a real binary, in CI, daily, on both the minimum and the latest CLI. Running that linter against CLI v0.4.42 — four weeks and sixteen patch versions after its last commit — surfaced two divergences. That is the command reference.

```text
/plugin marketplace add multica-ai/multica-cli
/plugin install multica-cli@multica-cli
```

It covers `issue search`, the comment read modes, the working-directory restriction on file arguments, when `--parent` is mandatory, the `mention://` side effects, metadata versus custom properties, subscribers, run inspection and cancellation, sub-issue stages, and PR linking. **This plugin restates none of it** — two skills describing the same commands eventually disagree, and a session obeys whichever it read first.

## What this one adds

- **Finding the binary in a desktop-app install.** The reference assumes `multica` is on `PATH`. With the desktop app it is not, `command -v multica` returns nothing, and the reference's very first step fails. Profile names come from `~/.multica/profiles`, workspaces from `workspace list`.
- **The bridged route.** Reaching the CLI from a Cowork or claude.ai session bridged to the machine running the desktop app — including the nested-quoting, non-zero-exit and cleanup traps of that path.
- **Shell gotchas that have produced real defects.** zsh collapsing a flag-holding variable into a single argument (the reason for the `mt()` wrapper), `for x in $VAR` iterating once, 1-indexed arrays, lowercase `pipestatus`, `$?` after a pipeline, BSD grep without `\s`.
- **Shapes and cost flags the reference omits**, measured on v0.4.42: `--limit` caps at 100 and paging advances by the count actually returned (`has_more`), `issue list --fields` trims agent context cost, `issue children` is not an array, `issue comment list` is a bare list, `autopilot get` is wrapped, `status_category` collapses custom statuses, `issue timeline` exists, and the `--content-stdin` family sidesteps the working-directory restriction on macOS.
- **Platform limits.** Workspace isolation and what it means for anything you write that governs agents; artifacts disabled inside agent tasks, subagents included; no MCP surface on the CLI, but agents *consume* MCP servers via `agent update --mcp-config`; cron-scheduled autopilots with IANA timezones and creation-time subscribers.
- **Governance.** The part that only matters if you work this way: a board whose agent instructions, workspace skills, context and project descriptions are versioned in a repository and deployed through the CLI. What to read there and in what order, and the eight constraints such a repo encodes — starting with the one that causes the most false statements about a live system: **editing is not deploying**.

## Install

```
/plugin marketplace add fernando-bertholdo/4-successful-AI-life
/plugin install multica-ops@4-successful-ai-life
/reload-plugins
```

## Use

Model-invoked; to pull it in explicitly:

```
/multica-ops:board
```

## Configuration

| Variable | What it does |
|---|---|
| `MULTICA_BIN` | Path to the `multica` binary. Defaults to the macOS desktop-app location. |
| `MULTICA_PROFILE` | Profile name. The available names are the directories under `~/.multica/profiles`. |
| `MULTICA_PLAYBOOK` | Path to the repository that versions your Multica configuration. When set, that repo — its agent-context file, manifests, drift check and deploy script — outranks this skill on everything it declares. |

Nothing board-specific ships in this plugin: no workspace ids, no project names, no machine paths.

## Compatibility

Measured against **Multica CLI v0.4.42**, and against the official skill at its **v1.1.0**. Both move; the skill instructs you to record `multica --version` next to any claim about the surface. If the reference grows to cover something documented here, that overlap is a bug in this plugin — [open an issue](https://github.com/fernando-bertholdo/4-successful-AI-life/issues).

## License

MIT — see [LICENSE](./LICENSE).
