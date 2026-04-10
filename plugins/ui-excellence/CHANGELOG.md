# Changelog — ui-excellence

All notable changes to the `ui-excellence` plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0-alpha.2] — 2026-04-10

### Added
- Eight skills adopted from [wondelai/skills](https://github.com/wondelai/skills) (MIT, commit `4d322538`, 2026-04-05):
  - `systems/refactoring/` — Wathan & Schoger's *Refactoring UI* (visual hierarchy, spacing, color, depth).
  - `systems/typography/` — Jason Santa Maria's *On Web Typography* (typeface selection, pairing, responsive type).
  - `audit/heuristics/` — Nielsen's heuristics + Krug's usability principles (severity ratings, cognitive walkthrough).
  - `audit/cro/` — Blanks & Jesson's CRO methodology (funnel mapping, A/B testing, objection handling).
  - `interaction/microinteractions/` — Dan Saffer's framework (triggers, rules, feedback, loops).
  - `behavior/hooked/` — Nir Eyal's Hook Model (trigger→action→variable reward→investment).
  - `behavior/retention/` — BJ Fogg's behavior design (B=MAP, Ability Chain, tiny habits).
  - `behavior/copy/` — Chip & Dan Heath's *Made to Stick* (SUCCESs checklist).
- Each adopted SKILL.md includes an Attribution footer with link to original source.
- Each adopted skill includes its `references/` directory with auxiliary documents.

### Changed
- `plugin.json`: skills array expanded from 4 to 12 paths. Version bumped to `1.0.0-alpha.2`.
- `marketplace.json`: description and keywords updated to reflect full 12-skill scope.
- `LICENSE`: updated from single-MIT to dual-MIT with wondelai attribution and provenance table.
- `README.md`: complete rewrite listing all 12 skills by group with invoke commands and attribution.
- Frontmatter `name` fields of adopted skills shortened per G-CANONICAL guardrail:
  `refactoring-ui` → `refactoring`, `web-typography` → `typography`,
  `ux-heuristics` → `heuristics`, `cro-methodology` → `cro`,
  `hooked-ux` → `hooked`, `improve-retention` → `retention`,
  `made-to-stick` → `copy`. `microinteractions` unchanged.

### Notes
- Cross-references to wondelai skills not present in this plugin (`top-design`,
  `contagious`, `drive-motivation`, `storybrand-messaging`, `one-page-marketing`,
  `design-everyday-things`) appear in description fields of adopted skills. These are
  navigational hints, not functional dependencies. Preserved per DL-2 (no rewriting).
- Content body of all 8 adopted skills is verbatim from wondelai/skills commit
  `4d322538`. Zero semantic modifications — only frontmatter name and attribution
  footer were changed.

### Deferred to `v1.0.0-alpha.3`
- `_coordinator/` skill with expanded routing logic and `paths:` frontmatter for
  auto-loading on UI file edits.

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
