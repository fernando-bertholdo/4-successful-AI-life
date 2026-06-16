# Changelog — generate-session-prompt (wrapper)

Este changelog rastreia o **wrapper** deste plugin (nosso código + nossos
patches). O changelog do skill upstream vive em `upstream/` (se existir).

Formato: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) +
versionamento `MAJOR.MINOR.PATCH+upstream-X.Y.Z`.

## [1.0.1+upstream-4.0.0] — 2026-06-16

### Changed
- Sync do upstream (commit `da4b05c`): correção do path de patches no procedimento
  de coleta do MODE:opinionated-initiative — `.planning/patches.md` →
  `.planning/patches/{slug}/plan.md`. Reflete reorganização da estrutura de patches
  no `tech-product-template`. Versão da skill upstream permanece `4.0.0` (não há
  bump de semver para correção textual desta natureza).

## [1.0.0+upstream-4.0.0] — 2026-04-28

### Added
- Vendor inicial de `tech-product-template/.claude/skills/generate-session-prompt/`
  (upstream SHA `284100f`, versão `4.0.0`).
- `plugin.json` declarando o skill em `./upstream/`.
- Workflow `.github/workflows/sync-generate-session-prompt.yml` para sync automático
  semanal (delega ao reusable `_sync-skill-from-template.yml`).

### Notes
- Sem patches locais nesta versão — o conteúdo do skill é idêntico ao upstream.
