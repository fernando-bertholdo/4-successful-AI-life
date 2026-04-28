# generate-session-prompt (vendored)

Wrapper de plugin Claude Code que vendoriza a skill `generate-session-prompt` do repositório
[`fernando-bertholdo/tech-product-template`](https://github.com/fernando-bertholdo/tech-product-template)
e a distribui via este marketplace.

## Origem

- **Upstream:** `tech-product-template/.claude/skills/generate-session-prompt/`
- **Snapshot inicial:** upstream `v4.0.0` (SHA `284100f`)
- **Licença upstream:** MIT (preservada em `upstream/` se aplicável)

O conteúdo da skill vive em `upstream/` e é puxado via sparse-checkout pelo
workflow `.github/workflows/sync-generate-session-prompt.yml`. Não edite arquivos em
`upstream/` por capricho — qualquer alteração ali é considerada um **patch
local** e deve seguir as regras abaixo.

## Versionamento

Formato: `MAJOR.MINOR.PATCH+upstream-X.Y.Z` (semver puro do wrapper +
build metadata identificando o snapshot do upstream vendorizado).

Veja `/CLAUDE.md` na raiz do marketplace para a tabela completa de bumps.

## Patches locais

Edite arquivos em `upstream/` diretamente, sempre delimitando o bloco com
sentinelas:

```markdown
<!-- LOCAL-PATCH:start id=identificador-curto -->
... seu conteúdo ...
<!-- LOCAL-PATCH:end id=identificador-curto -->
```

Documente cada patch no `CHANGELOG.md` deste diretório.

## Sync com upstream

**Automático:** workflow `.github/workflows/sync-generate-session-prompt.yml` roda
toda segunda-feira 09:00 UTC e abre PR se houver mudanças.

**Manual:**

```bash
gh workflow run sync-generate-session-prompt.yml
```
