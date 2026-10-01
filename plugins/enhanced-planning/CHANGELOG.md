# Changelog — enhanced-planning (wrapper)

Este changelog rastreia o **wrapper** deste plugin (nosso código + nossos
patches). O changelog do skill upstream vive em `upstream/` (se existir).

Formato: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) +
versionamento `MAJOR.MINOR.PATCH+upstream-X.Y.Z`.

## [1.1.0+upstream-2.0.0] — 2026-10-01

### Changed
- Sync do upstream `tech-product-template@4e775d5` (o vendor era `da4b05c`), o primeiro desde o
  vendor: os syncs semanais de 20/07 a 28/09/2026 falharam por autenticação do `UPSTREAM_TOKEN`,
  regravado em 30/09/2026, e este rodou por disparo manual.
- Comportamento novo que chega com o sync: o "Quando NAO Usar" troca "patches rapidos (<=2
  sessoes)" por "correcoes pontuais sem risco de regressao, que nao alteram o plano", e o
  checklist de documentação do `references/plan-template.md` deixa de pedir o `TODO.md`. Só texto:
  a anotação `@runtime-placeholders` no fim do `SKILL.md`.
- MINOR no wrapper porque o comportamento mudou com o upstream parado em `2.0.0` (linha da tabela
  de bump para esse caso, no `CLAUDE.md` da raiz).

### Local patches
- `standalone-usage` re-aplicado sem mudança pelo `scripts/reapply-local-patches.py`: o
  `upstream/SKILL.md` difere do da origem só pelo bloco entre as sentinelas, e os três
  `references/` são idênticos aos da origem.

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
