# Changelog — multica-ops

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-09-10

### Added

- First release. One skill, `board`: the operating manual for a Multica board from Claude Code
  or from a Cowork/claude.ai session bridged to the machine running the desktop app.
- Discovery-first design: the profile comes from `~/.multica/profiles`, the workspaces from
  `workspace list --output json`, and every other id from the corresponding `list` command.
  No workspace id, project name or machine-specific path is embedded in the plugin.
- Safe defaults documented as conventions rather than enforcement: `--no-start` on every
  `issue status`, silence on unscoped issues, promotion and deployment reserved for a human,
  no casual `create` of registry objects, and a dated trace when a session acts under a
  human's profile.
- Measured platform notes against **CLI v0.4.42**: the 100-item page cap on `--limit`, the
  `{stages, total, unstaged}` shape of `issue children`, the bare list from
  `issue comment list`, the `{"autopilot": …}` wrapper, the positional label argument on
  `issue label add`, `--name` (not `--property-id`) on `issue property set`, labels not
  inherited through `--parent`, the 255-character cap on `agent create --description`, and the
  absence of a global run listing.
- Shell gotchas that have produced real defects: zsh collapsing a flag-holding variable into a
  single argument (the reason for the `mt()` wrapper), `for x in $VAR` iterating once,
  1-indexed arrays, lowercase `pipestatus`, `$?` after a pipeline, and BSD grep's lack of `\s`.
- Platform limits: per-workspace isolation (only a human profile's CLI sees more than one),
  artifacts disabled inside agent tasks including subagents, and no MCP surface in the binary.
- `MULTICA_PLAYBOOK` hand-off: when a repository versions the Multica configuration, the skill
  defers to its manifests, drift check and deploy script instead of acting directly.
