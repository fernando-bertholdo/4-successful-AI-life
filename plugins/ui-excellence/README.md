# ui-excellence

UI/UX foundations for web interfaces.

**Version:** `1.0.0-alpha.1`
**License:** MIT
**Marketplace:** [`4-successful-ai-life`](../../README.md)

> **Alpha scope:** This release ships the 4 **foundations** skills (animation/motion, visual polish, web standards, accessibility). Upcoming alphas will add typography, microinteractions, heuristic audits, CRO methodology, and engagement loops — see [Coming in Future Alphas](#coming-in-future-alphas).

---

## What This Plugin Does

`ui-excellence` bundles opinionated, production-ready skills for web interface work. Each skill is framework-agnostic and focuses on decisions, trade-offs, and concrete checklists rather than boilerplate code.

The `v1.0.0-alpha.1` release covers the **foundations** layer: low-level motion, visual polish, general web standards, and full accessibility compliance. Additional layers (systems, audit, interaction, behavior) are scoped for future alphas.

The plugin is designed for two modes of use:

1. **On-demand invocation** — call individual skills when you need targeted guidance (`/ui-excellence:animation-motion` for motion decisions, `/ui-excellence:accessibility` for WCAG reviews, etc.).
2. **Path-aware auto-loading** *(coming in a later release)* — a coordinator skill will auto-load when editing UI files (`*.tsx`, `*.vue`, `*.svelte`, `*.css`, `*.scss`, `*.html`) and route to the right specialist based on signals in your prompt.

---

## Skills in This Release (`v1.0.0-alpha.1`)

This alpha ships the **foundations** group — the four core skills migrated from the `tech-product-template` baseline. More skills land in upcoming alphas.

### `foundations/animation-motion`
Motion and animation decisions grounded in Emil Kowalski's framework: when to animate, easing curves, spring physics, performance (60fps discipline), accessibility (`prefers-reduced-motion`), and gesture handling.

**Invoke as:** `/ui-excellence:animation-motion`

### `foundations/visual-polish`
Refinement of visual details that compound into a polished, cohesive experience. Following Jakub Krehel's principles: text wrapping strategies, balanced border radius hierarchies, optical alignment, shadow composition, contextual micro-animations.

**Invoke as:** `/ui-excellence:visual-polish`

### `foundations/web-standards`
Comprehensive guidance aligned with Vercel's Web Interface Guidelines: accessibility compliance (WCAG 2.1 AA), component patterns, form handling, typography, performance, navigation, and anti-patterns to avoid.

**Invoke as:** `/ui-excellence:web-standards`

### `foundations/accessibility`
Full WCAG 2.1 Level AA implementation and review guide: keyboard navigation, semantic HTML, ARIA attributes, color contrast, screen reader support, and assistive technology compatibility.

**Invoke as:** `/ui-excellence:accessibility`

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

## Coming in Future Alphas

The plugin's full scope includes 13 skills organized in six groups. The `v1.0.0-alpha.1` release contains only `foundations/` (4 skills). Upcoming releases will add:

- **`systems/`** — refactoring-ui and web-typography (adapted from [wondelai/skills](https://github.com/wondelai/skills), MIT)
- **`audit/`** — Nielsen heuristics and CRO methodology (adapted from wondelai/skills, MIT)
- **`interaction/`** — microinteractions (adapted from wondelai/skills, MIT)
- **`behavior/`** — Hooked model (Nir Eyal), retention loops, and Made-to-Stick copywriting (adapted from wondelai/skills, MIT)
- **`_coordinator/`** — triage skill with `paths:` frontmatter for auto-loading when editing UI files

Wondelai attribution and dual-MIT licensing will be added to this plugin's [`LICENSE`](./LICENSE) when those skills land in `v1.0.0-alpha.2`.

See [`CHANGELOG.md`](./CHANGELOG.md) for release history.

---

## License

MIT — see [LICENSE](./LICENSE).

This plugin currently contains only original content authored by Fernando Bertholdo (migrated from the `tech-product-template` baseline). Future releases will incorporate MIT-licensed content from [wondelai/skills](https://github.com/wondelai/skills) with full attribution and dual-MIT licensing.
