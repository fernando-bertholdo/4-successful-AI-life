# CLAUDE.md — maintainer & agent context

This file is the canonical maintenance guide for the **4 Successful AI Life** marketplace.
It documents conventions (how to maintain), not the catalog (what exists) — the catalog's
single source of truth is [`.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json)
and each plugin's `.claude-plugin/plugin.json`.

For end-user install instructions and the plugin list, see [`README.md`](./README.md).
For the full Tier 1 → Tier 2 promotion workflow, see [`docs/promotion-runbook.md`](./docs/promotion-runbook.md).

---

## What this repo is

A personal Claude Code **plugin marketplace**. Two layers of manifest:

- `.claude-plugin/marketplace.json` — the catalog `/plugin install` reads (lists every plugin + version).
- `plugins/<name>/.claude-plugin/plugin.json` — each plugin's own manifest, declaring its `skills[]`.

The `README.md` is human-facing prose; it has no functional effect but is the first thing a
reader sees. **The manifests are the source of truth — keep the README in sync with them, never
the other way around.**

## Two kinds of plugin

| Kind | Examples | Source of skill content |
|---|---|---|
| **Native** | `ui-excellence`, `smart-session-rename-cc` | Authored/maintained directly in this repo under `plugins/<name>/skills/`. |
| **Vendored** | `prompt-master`, `generate-session-prompt` | Mirrored from an upstream repo into `plugins/<name>/upstream/`, refreshed weekly by a sync workflow. **Do not hand-edit `upstream/` casually** — any change there is a *local patch* and must follow the sentinel rules below. |

## Versioning convention (vendored plugins)

Vendored plugins carry build metadata identifying the embedded upstream snapshot:

Format: `MAJOR.MINOR.PATCH+upstream-X.Y.Z`

| Scenario | Bump |
|---|---|
| Upstream sync (no local-patch change) | only `+upstream-X.Y.Z` |
| Local patch that changes behavior | MINOR |
| Local-patch fix | PATCH |
| Refactor of patches due to an upstream breaking change | MAJOR |

The part before `+` is pure semver of **our wrapper** (our code). The part after `+` is build
metadata identifying the vendored upstream snapshot. Native plugins use plain semver with no
`+upstream` suffix.

## Local patches (vendored plugins)

Edit files under `upstream/` only when necessary, and always wrap the block in sentinels so a
future `subtree pull` / sparse-checkout sync can find and re-apply it:

```markdown
<!-- LOCAL-PATCH:start id=short-identifier -->
... your content ...
<!-- LOCAL-PATCH:end id=short-identifier -->
```

Document every patch in that plugin's own `CHANGELOG.md` (separate from the upstream changelog).

## Sync workflows

Weekly automated upstream sync lives in [`.github/workflows/`](./.github/workflows/):

- `sync-prompt-master.yml` — `git subtree pull` from `nidhinjs/prompt-master`.
- `sync-generate-session-prompt.yml` — trigger that delegates to the reusable
  `_sync-skill-from-template.yml` (sparse-checkout from the private `tech-product-template`).

Both run Mondays 09:00 UTC, open a PR when the upstream advances, and open an auto-deduplicated
`[sync-failure] <skill>` issue if the workflow fails. The sparse-checkout from the private
upstream needs the `UPSTREAM_TOKEN` secret (see the promotion runbook for PAT setup/rotation).

**Merge sync PRs with `--merge`, never `--squash`** — squash collapses the `chore(...): sync from ...`
commits that document which upstream snapshot is embedded in which of our commits.

---

## Anti-drift checklist — when you add or change a plugin

The README drifted from the catalog before because these touchpoints were updated by hand and
some were missed. When a plugin is **added, renamed, or version-bumped**, update *all* of:

1. `plugins/<name>/.claude-plugin/plugin.json` — version + `skills[]` (the authoritative manifest).
2. `.claude-plugin/marketplace.json` — the plugin's catalog entry (version, description, keywords)
   **and** bump the top-level `metadata.version` for the marketplace release.
3. `README.md` — the **Available Plugins** table, both install blocks (Option 1 + Option 2), the
   `settings.json` `enabledPlugins` example, and the **Structure** tree.
4. `CHANGELOG.md` (root) — a marketplace-level entry; cross-link the plugin's own changelog.
5. `plugins/<name>/CHANGELOG.md` — the plugin-level entry.
6. `plugins/<name>/README.md` — keep skill counts and version headers consistent with `plugin.json`.

Quick consistency check before committing:

```bash
# catalog is valid and lists what you expect
python3 -c "import json; d=json.load(open('.claude-plugin/marketplace.json')); print(len(d['plugins']), 'plugins:', ', '.join(p['name'] for p in d['plugins']))"

# a plugin's declared skill count matches its SKILL.md files on disk
find plugins/<name> -name SKILL.md | wc -l
python3 -c "import json; print(len(json.load(open('plugins/<name>/.claude-plugin/plugin.json'))['skills']))"
```
