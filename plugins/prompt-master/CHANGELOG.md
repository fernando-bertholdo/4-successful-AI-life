# Changelog — prompt-master (wrapper)

Este changelog rastreia o **wrapper** deste plugin (nosso código + nossos patches). O changelog do skill upstream vive em `upstream/` e é movido pelos próprios commits do Nidhin.

Formato: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + versionamento `MAJOR.MINOR.PATCH+upstream-X.Y.Z`.

## [1.0.0+upstream-1.7.0] — 2026-06-16

### Changed
- Sync do upstream: `nidhinjs/prompt-master` avançou `v1.6.0` → `v1.7.0`.
  Sem patches locais a re-aplicar (não temos sentinelas `LOCAL-PATCH`).

### Upstream highlights (v1.7.0)
- **Compatibilidade com Opus 4.7/4.8**: routing de Claude 4.x agora é
  version-aware (commits `98837a5`, `19e700d`)
- **Hardening de segurança NLP**: redução de "vague attack surface area"
  (commit `194826a`)
- **Compressão de seções abaixo de 450 linhas**: reduz token cost da skill
  preservando comportamento (commit `9d64012`)
- **Template M (Opus 4.7 Task Brief)**: novo template (commit `e8b49b7`)
- **Patterns 36-37**: novos padrões para falhas de prompt do Opus 4.7
  (commit `0c21dfc`)
- **Routing atualizado**: MiniMax M3 default, novos patterns para Opus 4.7,
  routing version-aware para Claude e Claude Code

### Wrapper changes (nossos)
- `description` em `plugin.json` atualizada para refletir a nova ativação
  restritiva: a skill **só ativa quando o usuário pede explicitamente** um
  prompt, não em tarefas gerais de código/conversa. Mudança importante de
  contrato para quem instalar — antes ativava amplamente, agora é precisa.

## [1.0.0+upstream-1.6.0] — 2026-04-27

### Added
- Vendor inicial do `nidhinjs/prompt-master` via `git subtree` em `plugins/prompt-master/upstream/` (upstream commit `19e700d`).
- `plugin.json` declarando o skill em `./upstream/`.
- Workflow `.github/workflows/sync-prompt-master.yml` para sync automático semanal com o upstream.

### Notes
- Sem patches locais nesta versão — o conteúdo do skill é idêntico ao upstream `1.6.0`.
