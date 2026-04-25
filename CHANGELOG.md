# Changelog — 4 Successful AI Life

All notable changes to this marketplace will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this marketplace adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
