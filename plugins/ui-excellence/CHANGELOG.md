# Changelog — ui-excellence

All notable changes to the `ui-excellence` plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0-alpha.1] — 2026-04-09

### Changed (2026-04-09, post-Codex review)
- `marketplace.json` plugin description, `plugin.json` description, and `README.md` intro rewritten to reflect the actual `v1.0.0-alpha.1` scope (4 foundations skills) instead of the aspirational 12+ skills scope. Aspirational content preserved in the "Coming in Future Alphas" section and in `marketplace.json` keywords.

### Added
- Initial plugin scaffold with `.claude-plugin/plugin.json` manifest.
- Four foundations skills migrated from the `tech-product-template` baseline:
  - `foundations/animation-motion/` — Emil Kowalski's motion framework.
  - `foundations/visual-polish/` — Jakub Krehel's visual refinement principles.
  - `foundations/web-standards/` — Vercel Web Interface Guidelines alignment.
  - `foundations/accessibility/` — WCAG 2.1 Level AA implementation guide.
- Plugin-level README, LICENSE (single-MIT), and this CHANGELOG.

### Notes
- Frontmatter `name` fields were shortened to remove the redundant `ui-` prefix
  (e.g., `ui-animation-motion` → `animation-motion`), following the G-CANONICAL
  guardrail of the ui-excellence-plugin initiative. Public namespace is therefore
  `ui-excellence:animation-motion` rather than `ui-excellence:ui-animation-motion`.
- SKILL.md body content is a verbatim copy of the `tech-product-template`
  originals — no semantic modifications.

### Deferred to `v1.0.0-alpha.2`
- Adoption of 8 skills from [wondelai/skills](https://github.com/wondelai/skills)
  (`refactoring-ui`, `web-typography`, `ux-heuristics`, `cro-methodology`,
  `microinteractions`, `hooked-ux`, `improve-retention`, `made-to-stick`) with
  MIT attribution and dual-MIT LICENSE update.

### Deferred to `v1.0.0-alpha.3`
- `_coordinator/` skill with expanded routing logic and `paths:` frontmatter for
  auto-loading on UI file edits.
