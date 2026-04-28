# Changelog — 4 Successful AI Life

All notable changes to this marketplace will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this marketplace adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.6.0] — 2026-04-28

### Added
- Fourth plugin: `generate-session-prompt` at `v1.0.0+upstream-4.0.0` (see [`plugins/generate-session-prompt/CHANGELOG.md`](./plugins/generate-session-prompt/CHANGELOG.md)). Promoted from the private `tech-product-template` repo via the new `scripts/promote-skill.sh` bootstrap. Skill ships with dual-mode behavior (`MODE:opinionated-initiative` for projects with `.planning/`, `MODE:generic` otherwise), making it useful in any project.
- `.github/workflows/sync-generate-session-prompt.yml` — trigger workflow that delegates to the reusable `_sync-skill-from-template.yml` for weekly automated upstream sync.

### Notes
- The first sync execution requires `UPSTREAM_TOKEN` secret (fine-grained PAT with `Contents: Read` on `tech-product-template`) to be configured per `docs/promotion-runbook.md`. Until then, the plugin works (initial vendor was done locally) but the weekly automated sync workflow will fail.

---

## [0.5.0] — 2026-04-27

### Added
- Third plugin: `prompt-master` at `v1.0.0+upstream-1.6.0` (see [`plugins/prompt-master/CHANGELOG.md`](./plugins/prompt-master/CHANGELOG.md)). Vendored from upstream [`nidhinjs/prompt-master`](https://github.com/nidhinjs/prompt-master) via `git subtree` into `plugins/prompt-master/upstream/`. The wrapper uses semver build metadata (`+upstream-X.Y.Z`) to track which upstream snapshot each release embeds.
- GitHub Actions workflow `.github/workflows/sync-prompt-master.yml` for weekly automated upstream sync — runs Mondays 09:00 UTC and opens a PR when the upstream advances.

---

## [0.4.0] — 2026-04-25

### Added
- Second plugin: `smart-session-rename-cc` at `v1.5.0` (see [`plugins/smart-session-rename-cc/CHANGELOG.md`](./plugins/smart-session-rename-cc/CHANGELOG.md)). Imported with full git history (51 commits) via `git filter-repo` from the standalone `claude-code-smart-session-rename` repository, which has been archived as `smart-session-rename-cc-archive`.

### Changed
- README adds installation snippets and skill examples for `smart-session-rename-cc`.
- Roadmap adds `smart-session-rename-cc` v1.5.1 (deferred bug fixes).

---

## [0.3.0] — 2026-04-10

### Changed
- `ui-excellence` plugin bumped to `v1.0.0-alpha.3`: added coordinator skill with triage routing for all 13 domains and `paths:` frontmatter. Plugin is now feature-complete for `v1.0.0`. See [`plugins/ui-excellence/CHANGELOG.md`](./plugins/ui-excellence/CHANGELOG.md).

---

## [0.2.0] — 2026-04-10

### Changed
- `ui-excellence` plugin bumped to `v1.0.0-alpha.2`: adopted 8 skills from [wondelai/skills](https://github.com/wondelai/skills) (MIT), expanding the plugin from 4 to 12 skills. See [`plugins/ui-excellence/CHANGELOG.md`](./plugins/ui-excellence/CHANGELOG.md) for details.
- `marketplace.json` plugin entry updated with expanded description, version, and keywords.

---

## [0.1.0] — 2026-04-09

### Added
- Initial marketplace scaffold with `.claude-plugin/marketplace.json`.
- First plugin: `ui-excellence` at `v1.0.0-alpha.1` (see [`plugins/ui-excellence/CHANGELOG.md`](./plugins/ui-excellence/CHANGELOG.md)).
- Repository-level README with three installation modes (GitHub, local clone, `--plugin-dir`).
- MIT license at repository level.
