# Contributing & maintaining

This marketplace is maintained for personal and project-specific use, so external contributions
aren't actively solicited — but issues and discussion are welcome on the
[issue tracker](https://github.com/fernando-bertholdo/4-successful-AI-life/issues).

This document is for **maintainers and the curious**: how the repo is laid out, how plugins get
here, and where the deeper conventions live. For day-to-day maintenance conventions — the
`+upstream-X.Y.Z` versioning scheme, local-patch sentinels, and the anti-drift checklist — see
[`CLAUDE.md`](./CLAUDE.md).

---

## Repository structure

```
4-successful-AI-life/
├── .claude-plugin/
│   └── marketplace.json       ← marketplace manifest (catalog source of truth)
├── .github/workflows/         ← weekly upstream-sync workflows (vendored plugins)
├── README.md                  ← public, user-facing
├── CLAUDE.md                  ← maintainer & agent conventions + anti-drift checklist
├── CONTRIBUTING.md            ← this file
├── LICENSE                    ← MIT (repository level)
├── CHANGELOG.md               ← marketplace release history
├── docs/promotion-runbook.md  ← Tier 1 → Tier 2 promotion workflow
├── scripts/promote-skill.sh   ← bootstrap a vendored plugin from the template
└── plugins/
    ├── ui-excellence/             ← UI/UX skill bundle
    │   ├── .claude-plugin/plugin.json   ← plugin manifest with skills array
    │   ├── skills/                ← one folder per skill (SKILL.md + references/)
    │   ├── README.md · LICENSE · CHANGELOG.md
    ├── smart-session-rename-cc/   ← Stop-hook auto-renamer
    │   ├── .claude-plugin/plugin.json
    │   ├── hooks/hooks.json       ← Stop hook registration
    │   ├── scripts/               ← rename-hook + smart-rename-cli + lib/
    │   ├── skills/smart-rename/   ← /smart-rename skill router
    │   ├── tests/                 ← unit + integration suites
    │   ├── docs/ · README.md · LICENSE · CHANGELOG.md
    ├── prompt-master/             ← vendored prompt-engineering skill
    │   ├── .claude-plugin/plugin.json
    │   ├── upstream/              ← git-subtree mirror of nidhinjs/prompt-master
    │   ├── README.md · CHANGELOG.md
    ├── generate-session-prompt/   ← vendored session-handoff skill
    │   ├── .claude-plugin/plugin.json
    │   ├── upstream/              ← sparse-checkout mirror of tech-product-template
    │   ├── README.md · CHANGELOG.md
    └── enhanced-planning/         ← vendored planning-guardrails skill
        ├── .claude-plugin/plugin.json
        ├── upstream/              ← SKILL.md + references/ (LOCAL-PATCH: standalone-usage)
        ├── README.md · CHANGELOG.md
```

Each plugin is fully self-contained under `plugins/<name>/` with its own manifest, docs, license,
and changelog.

## Two kinds of plugin

| Kind | Examples | Source of skill content |
|---|---|---|
| **Native** | `ui-excellence`, `smart-session-rename-cc` | Authored and maintained directly in this repo under `plugins/<name>/skills/`. |
| **Vendored** | `prompt-master`, `generate-session-prompt` | Mirrored from an upstream repo into `plugins/<name>/upstream/`, refreshed weekly by a sync workflow. Don't hand-edit `upstream/` casually — any change there is a *local patch* and must follow the sentinel rules in [`CLAUDE.md`](./CLAUDE.md). |

## Promoting a skill from `tech-product-template`

Skills are developed in the private `tech-product-template` repo (**Tier 1**, source of truth) and
promoted to this marketplace (**Tier 2**, distribution) via sparse-checkout / `git subtree` sync.
Movement is always Tier 1 → Tier 2, never the reverse.

The full workflow — architecture model, one-time fine-grained-PAT setup, the
`scripts/promote-skill.sh` bootstrap, and troubleshooting — lives in
[`docs/promotion-runbook.md`](./docs/promotion-runbook.md).

Weekly automated sync runs from [`.github/workflows/`](./.github/workflows/) (Mondays 09:00 UTC),
opening a PR when an upstream advances and an auto-deduplicated `[sync-failure] <skill>` issue if a
run fails. **Merge sync PRs with `--merge`, never `--squash`** — squash collapses the
`chore(...): sync from ...` commits that document which upstream snapshot is embedded in which of
our commits.

## Conventions

Before adding, renaming, or version-bumping a plugin, read the **anti-drift checklist** in
[`CLAUDE.md`](./CLAUDE.md) — it lists every touchpoint (the two manifests, the README, both
changelogs) that must stay in sync, plus a quick consistency check to run before committing.
