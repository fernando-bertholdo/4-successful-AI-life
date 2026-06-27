# Changelog — enhanced-planning (wrapper)

Este changelog rastreia o **wrapper** deste plugin (nosso código + nossos
patches). O changelog do skill upstream vive em `upstream/` (se existir).

Formato: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) +
versionamento `MAJOR.MINOR.PATCH+upstream-X.Y.Z`.

## [1.0.0+upstream-2.0.0] — 2026-06-27

### Added
- Vendor inicial de `tech-product-template/.claude/skills/enhanced-planning/`
  (upstream SHA `da4b05c`, versão `2.0.0`).
- `plugin.json` declarando o skill em `./upstream/`.
- Workflow `.github/workflows/sync-enhanced-planning.yml` para sync automático
  semanal (delega ao reusable `_sync-skill-from-template.yml`).

### Local patches
- `standalone-usage` (em `upstream/SKILL.md`) — preâmbulo "Standalone usage" que torna o
  skill utilizável fora do `tech-product-template`: mapeia o jargão (milestone/detour/initiative),
  define um default para `{{PLANNING_DIR}}`, e enquadra os skills-companion (`init-milestone`,
  `validate-dor`/`validate-dod`, `archive-initiative`) como opcionais. O corpo do upstream
  permanece idêntico, para que os syncs semanais fiquem limpos.
