# 4 Successful AI Life

Curated plugins for AI-assisted work — focused on craft, rigor, and practical excellence.

> A personal marketplace of Claude Code plugins by [Fernando Bertholdo](https://github.com/fernando-bertholdo).

---

## Available Plugins

| Plugin | Version | Description |
|---|---|---|
| [`ui-excellence`](./plugins/ui-excellence/) | `1.0.0-alpha.3` | 13 skills with triage coordinator for UI/UX craft: visual design, typography, accessibility, usability audits, CRO, microinteractions, and engagement loops. |
| [`smart-session-rename-cc`](./plugins/smart-session-rename-cc/) | `1.5.0` | Auto-name your Claude Code sessions. Stop hook + work-score throttle + Haiku-generated `domain: clauses` titles, with seven `/smart-rename` subcommands for manual override. |
| [`prompt-master`](./plugins/prompt-master/) | `1.0.0+upstream-1.7.0` | Generates optimized prompts for AI tools (LLMs, image/video AI, coding agents). Activates only on explicit prompt-engineering requests. Vendored from [`nidhinjs/prompt-master`](https://github.com/nidhinjs/prompt-master), kept in sync weekly via GitHub Action. |
| [`generate-session-prompt`](./plugins/generate-session-prompt/) | `1.0.1+upstream-4.0.0` | Generates a handoff prompt to resume work in a new session — for long sessions, pauses, or tool switches. Dual-mode: opinionated when `.planning/` exists, generic otherwise. Vendored from `tech-product-template`, synced weekly. |

More plugins are planned — see the [roadmap](#roadmap) below.

---

## Installing Plugins

There are three ways to install plugins from this marketplace, depending on your use case.

### Option 1 — From GitHub (recommended for normal use)

Inside a Claude Code session, register the marketplace and install the plugin you want:

```
/plugin marketplace add fernando-bertholdo/4-successful-AI-life
/plugin install ui-excellence@4-successful-ai-life
/plugin install smart-session-rename-cc@4-successful-ai-life
/plugin install prompt-master@4-successful-ai-life
/plugin install generate-session-prompt@4-successful-ai-life
/reload-plugins
```

After reload, skills become invocable under the plugin namespace:

```
/ui-excellence:animation-motion
/ui-excellence:visual-polish
/ui-excellence:web-standards
/ui-excellence:accessibility
/smart-rename                  # bare — suggest a title now
/smart-rename explain          # show current state snapshot
/smart-rename freeze           # pause auto-rename
/generate-session-prompt           # handoff prompt, mode auto-detected
/generate-session-prompt detailed  # detailed variant (brief | standard | detailed)
```

`prompt-master` is model-invoked: it activates automatically when you explicitly ask Claude to write, fix, improve, or adapt a prompt for a specific AI tool — no slash command needed.

### Option 2 — From a local clone (recommended for development)

Clone this repository and add the local path as a marketplace:

```bash
git clone https://github.com/fernando-bertholdo/4-successful-AI-life.git
cd 4-successful-AI-life
```

Then, inside a Claude Code session launched from the clone directory:

```
/plugin marketplace add ./
/plugin install ui-excellence@4-successful-ai-life
/plugin install smart-session-rename-cc@4-successful-ai-life
/plugin install prompt-master@4-successful-ai-life
/plugin install generate-session-prompt@4-successful-ai-life
/reload-plugins
```

This mode is useful when you want to hack on a plugin locally before pushing changes.

### Option 3 — Via `--plugin-dir` (quick single-plugin test)

Bypass the marketplace entirely and load a single plugin directly:

```bash
claude --plugin-dir ./plugins/ui-excellence
```

This mode is handy for validating a plugin in isolation without touching your global marketplace registry.

### Permanent opt-in via `settings.json`

To auto-install the plugin in a project, add to `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "4-successful-ai-life": {
      "source": {
        "source": "github",
        "repo": "fernando-bertholdo/4-successful-AI-life"
      }
    }
  },
  "enabledPlugins": {
    "ui-excellence@4-successful-ai-life": true,
    "smart-session-rename-cc@4-successful-ai-life": true,
    "prompt-master@4-successful-ai-life": true,
    "generate-session-prompt@4-successful-ai-life": true
  }
}
```

Claude Code will prompt you to trust the marketplace on first open, then keep the plugin available across sessions.

---

## Structure

```
4-successful-AI-life/
├── .claude-plugin/
│   └── marketplace.json       ← marketplace manifest (catalog source of truth)
├── .github/workflows/         ← weekly upstream-sync workflows (vendored plugins)
├── README.md                  ← this file
├── CLAUDE.md                  ← maintainer & agent context (conventions, anti-drift checklist)
├── LICENSE                    ← MIT (repository level)
├── CHANGELOG.md               ← marketplace release history
├── docs/promotion-runbook.md  ← Tier 1 → Tier 2 promotion workflow
├── scripts/promote-skill.sh   ← bootstrap a vendored plugin from the template
└── plugins/
    ├── ui-excellence/             ← UI/UX skill bundle
    │   ├── .claude-plugin/
    │   │   └── plugin.json        ← plugin manifest with skills array
    │   ├── README.md
    │   ├── LICENSE
    │   ├── CHANGELOG.md
    │   └── skills/
    ├── smart-session-rename-cc/   ← Stop-hook auto-renamer
    │   ├── .claude-plugin/
    │   │   └── plugin.json
    │   ├── hooks/hooks.json       ← Stop hook registration
    │   ├── scripts/               ← rename-hook + smart-rename-cli + lib/
    │   ├── skills/smart-rename/   ← /smart-rename skill router
    │   ├── tests/                 ← unit + integration suites
    │   ├── docs/
    │   ├── README.md
    │   ├── LICENSE
    │   └── CHANGELOG.md
    ├── prompt-master/             ← vendored prompt-engineering skill
    │   ├── .claude-plugin/
    │   │   └── plugin.json
    │   ├── upstream/              ← git-subtree mirror of nidhinjs/prompt-master
    │   │   ├── SKILL.md
    │   │   └── references/
    │   ├── README.md              ← vendoring + local-patch rules
    │   └── CHANGELOG.md
    └── generate-session-prompt/   ← vendored session-handoff skill
        ├── .claude-plugin/
        │   └── plugin.json
        ├── upstream/              ← sparse-checkout mirror of tech-product-template
        │   └── SKILL.md
        ├── README.md
        └── CHANGELOG.md
```

Each plugin is fully self-contained under `plugins/<name>/` and has its own manifest, docs, license, and changelog. The two vendored plugins (`prompt-master`, `generate-session-prompt`) keep their upstream source under `upstream/` and are refreshed weekly by the sync workflows in [`.github/workflows/`](./.github/workflows/).

---

## Roadmap

- **`ui-excellence` v1.0.0** — Expand foundations (4 skills) with adopted [wondelai/skills](https://github.com/wondelai/skills) content (8 skills) plus a coordinator with routing logic and path-targeting. See project-level planning in the consumer repos.
- **`smart-session-rename-cc` v1.5.1** — Fix two CLI-path bugs surfaced during Level 4 testing (state empty-write under degenerate transcripts; `/smart-rename force` state divergence). See `plugins/smart-session-rename-cc/docs/superpowers/handoff/2026-04-20-known-issues.md` for the investigation notes.
- **Future plugins** — `planning-suite`, `sync-toolkit`, `design-sprint`, and other focused bundles extracted from long-running workflows.

---

## License

MIT — see [LICENSE](./LICENSE).

Individual plugins may carry additional attribution in their own LICENSE files when they incorporate third-party content.

---

## Contributing

This marketplace is currently maintained for personal and project-specific use. External contributions are not actively solicited, but issues and discussion are welcome on the [GitHub issue tracker](https://github.com/fernando-bertholdo/4-successful-AI-life/issues).

---

## Internal — Promoting skills from `tech-product-template`

Skills are developed in the private `tech-product-template` repo (Tier 1) and promoted to this marketplace (Tier 2) via sparse-checkout sync. See [`docs/promotion-runbook.md`](./docs/promotion-runbook.md) for the architecture model, one-time PAT setup, and the `scripts/promote-skill.sh` workflow.

For maintenance conventions — native vs. vendored plugins, the `+upstream-X.Y.Z` versioning scheme, local-patch sentinels, and the anti-drift checklist to follow when adding or bumping a plugin — see [`CLAUDE.md`](./CLAUDE.md).
