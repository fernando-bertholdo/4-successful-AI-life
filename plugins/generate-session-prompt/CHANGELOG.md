# Changelog — generate-session-prompt (wrapper)

Este changelog rastreia o **wrapper** deste plugin (nosso código + nossos
patches). O changelog do skill upstream vive em `upstream/` (se existir).

Formato: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) +
versionamento `MAJOR.MINOR.PATCH+upstream-X.Y.Z`.

## [1.0.0+upstream-4.0.0] — 2026-04-28

### Added
- Vendor inicial de `tech-product-template/.claude/skills/generate-session-prompt/`
  (upstream SHA `284100f`, versão `4.0.0`).
- `plugin.json` declarando o skill em `./upstream/`.
- Workflow `.github/workflows/sync-generate-session-prompt.yml` para sync automático
  semanal (delega ao reusable `_sync-skill-from-template.yml`).

### Notes
- Sem patches locais nesta versão — o conteúdo do skill é idêntico ao upstream.
