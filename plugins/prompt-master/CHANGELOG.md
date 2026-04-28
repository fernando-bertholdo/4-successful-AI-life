# Changelog — prompt-master (wrapper)

Este changelog rastreia o **wrapper** deste plugin (nosso código + nossos patches). O changelog do skill upstream vive em `upstream/` e é movido pelos próprios commits do Nidhin.

Formato: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + versionamento `MAJOR.MINOR.PATCH+upstream-X.Y.Z`.

## [1.0.0+upstream-1.6.0] — 2026-04-27

### Added
- Vendor inicial do `nidhinjs/prompt-master` via `git subtree` em `plugins/prompt-master/upstream/` (upstream commit `19e700d`).
- `plugin.json` declarando o skill em `./upstream/`.
- Workflow `.github/workflows/sync-prompt-master.yml` para sync automático semanal com o upstream.

### Notes
- Sem patches locais nesta versão — o conteúdo do skill é idêntico ao upstream `1.6.0`.
