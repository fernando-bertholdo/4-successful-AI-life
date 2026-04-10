# ui-excellence

Comprehensive UI/UX skills for web interfaces — 13 skills (12 specialists + 1 triage coordinator) spanning visual design, typography, accessibility, usability audits, conversion optimization, microinteractions, and engagement loops.

**Version:** `1.0.0-alpha.3`
**License:** MIT (dual — see [LICENSE](./LICENSE) for wondelai attribution)
**Marketplace:** [`4-successful-ai-life`](../../README.md)

---

## What This Plugin Does

`ui-excellence` bundles opinionated, production-ready skills for web interface work. Each skill is framework-agnostic and focuses on decisions, trade-offs, and concrete checklists rather than boilerplate code.

The plugin is designed for two modes of use:

1. **On-demand invocation** — call individual skills when you need targeted guidance (`/ui-excellence:animation-motion` for motion decisions, `/ui-excellence:heuristics` for usability audits, etc.).
2. **Path-aware auto-loading** *(coming in a later release)* — a coordinator skill will auto-load when editing UI files (`*.tsx`, `*.vue`, `*.svelte`, `*.css`, `*.scss`, `*.html`) and route to the right specialist based on signals in your prompt.

---

## Skills (`v1.0.0-alpha.2` — 12 skills)

### Foundations (original)

Skills migrated from the `tech-product-template` baseline.

| Skill | Invoke as | Description |
|---|---|---|
| `foundations/animation-motion` | `/ui-excellence:animation-motion` | Emil Kowalski's motion framework: easing, springs, 60fps, `prefers-reduced-motion`, gestures. |
| `foundations/visual-polish` | `/ui-excellence:visual-polish` | Jakub Krehel's principles: text wrapping, border radius, optical alignment, shadow composition. |
| `foundations/web-standards` | `/ui-excellence:web-standards` | Vercel Web Interface Guidelines: WCAG 2.1 AA, component patterns, forms, performance. |
| `foundations/accessibility` | `/ui-excellence:accessibility` | Full WCAG 2.1 AA implementation: keyboard nav, semantic HTML, ARIA, color contrast, screen readers. |

### Systems (adapted from [wondelai/skills](https://github.com/wondelai/skills))

Macro-level design systems and typography.

| Skill | Invoke as | Description |
|---|---|---|
| `systems/refactoring` | `/ui-excellence:refactoring` | Audit and fix visual hierarchy, spacing, color, depth. Grayscale-first workflow, constrained scales, design tokens. Based on Wathan & Schoger's *Refactoring UI*. |
| `systems/typography` | `/ui-excellence:typography` | Typeface selection, pairing, responsive type, web font loading, performance. Based on Jason Santa Maria's *On Web Typography*. |

### Audit (adapted from [wondelai/skills](https://github.com/wondelai/skills))

Usability evaluation and conversion optimization.

| Skill | Invoke as | Description |
|---|---|---|
| `audit/heuristics` | `/ui-excellence:heuristics` | Nielsen's 10 heuristics, Krug's usability principles, severity ratings, cognitive walkthrough, information architecture. |
| `audit/cro` | `/ui-excellence:cro` | CRO methodology: funnel mapping, A/B testing, objection handling, persuasion assets. Based on Blanks & Jesson's *Making Websites Win*. |

### Interaction (adapted from [wondelai/skills](https://github.com/wondelai/skills))

Micro-level interaction details.

| Skill | Invoke as | Description |
|---|---|---|
| `interaction/microinteractions` | `/ui-excellence:microinteractions` | Trigger design, state rules, feedback mechanisms, progressive loops. Based on Dan Saffer's framework. |

### Behavior (adapted from [wondelai/skills](https://github.com/wondelai/skills))

Engagement, retention, and persuasion.

| Skill | Invoke as | Description |
|---|---|---|
| `behavior/hooked` | `/ui-excellence:hooked` | Hook Model (Trigger→Action→Variable Reward→Investment). Ethics evaluation, habit testing. Based on Nir Eyal's *Hooked*. |
| `behavior/retention` | `/ui-excellence:retention` | Behavior design (B=MAP), Ability Chain, activation milestones, tiny habits. Based on BJ Fogg's research. |
| `behavior/copy` | `/ui-excellence:copy` | SUCCESs checklist (Simple, Unexpected, Concrete, Credible, Emotional, Stories). Based on Chip & Dan Heath's *Made to Stick*. |

---

## Installing

### Through the marketplace (recommended)

```
/plugin marketplace add fernando-bertholdo/4-successful-AI-life
/plugin install ui-excellence@4-successful-ai-life
/reload-plugins
```

### Via a local clone

```bash
git clone https://github.com/fernando-bertholdo/4-successful-AI-life.git
cd 4-successful-AI-life
```

Then in Claude Code:

```
/plugin marketplace add ./
/plugin install ui-excellence@4-successful-ai-life
/reload-plugins
```

### Directly via `--plugin-dir`

```bash
claude --plugin-dir /path/to/4-successful-AI-life/plugins/ui-excellence
```

See the [marketplace-level README](../../README.md#installing-plugins) for the full installation guide including `settings.json` auto-install.

---

## Coordinator

The `_coordinator` skill (`/ui-excellence:coordinator`) is a triage router that analyzes task context and loads the right specialist skill(s) automatically. It includes:

- Decision tree covering 12 task patterns (from "build a modal" to "engagement audit")
- Signal-based routing with specific file/prompt triggers for each skill
- 16-entry Multi-Routing table for common multi-skill combinations
- 9-layer priority order for applying multiple skills simultaneously
- `paths:` frontmatter for auto-loading when editing UI files (`*.tsx`, `*.vue`, `*.css`, etc.)

**Note:** `paths:` auto-loading in plugin skills is aspirational — empirical validation pending. The coordinator can always be invoked directly via `/ui-excellence:coordinator`.

## Feature Completeness

The `v1.0.0-alpha.3` release contains all 13 planned skills. The plugin is feature-complete for the `v1.0.0` milestone. Remaining work before `v1.0.0` release is integration and cleanup in the consumer repos (flat replication to `.codex/` and `.agents/`, settings.json configuration, and legacy skill cleanup).

See [`CHANGELOG.md`](./CHANGELOG.md) for release history.

---

## Cross-References to External Skills

Some wondelai skills reference other wondelai skills (e.g., "For typeface selection, see web-typography") in their description fields. These are navigational hints from the original catalog, not functional dependencies. Where the referenced skill exists in this plugin, it is accessible via the new namespace (e.g., `/ui-excellence:typography`). Where it does not exist in this plugin (e.g., `top-design`, `contagious`, `drive-motivation`, `storybrand-messaging`, `one-page-marketing`, `design-everyday-things`), the reference is a pointer to the original [wondelai/skills](https://github.com/wondelai/skills) catalog.

---

## License

MIT (dual) — see [LICENSE](./LICENSE).

This plugin contains:
- **Original content** authored by Fernando Bertholdo (`foundations/` group — 4 skills).
- **Adapted content** from [wondelai/skills](https://github.com/wondelai/skills), MIT-licensed, with attribution (`systems/`, `audit/`, `interaction/`, `behavior/` groups — 8 skills). See the LICENSE file for the full dual-MIT notice and provenance table.
