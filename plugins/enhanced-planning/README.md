# enhanced-planning (vendored)

Wrapper de plugin Claude Code que vendoriza a skill `enhanced-planning` do repositório
[`fernando-bertholdo/tech-product-template`](https://github.com/fernando-bertholdo/tech-product-template)
e a distribui via este marketplace.

## Origem

- **Upstream:** `tech-product-template/.claude/skills/enhanced-planning/`
- **Snapshot inicial:** upstream `v2.0.0` (SHA `da4b05c`)
- **Licença upstream:** MIT (preservada em `upstream/` se aplicável)

> **Uso standalone:** este skill nasceu num framework de planejamento por
> milestones/detours, mas funciona fora dele. Um patch local `standalone-usage`
> no topo do `upstream/SKILL.md` explica como mapear o jargão e quais skills-companion
> são opcionais. Pareia com `writing-plans` (do [superpowers](https://github.com/obra/superpowers)) e [`/codex:rescue`](https://github.com/openai/codex-plugin-cc) (plugin oficial do Codex pra Claude Code, da OpenAI).

O conteúdo da skill vive em `upstream/` e é puxado via sparse-checkout pelo
workflow `.github/workflows/sync-enhanced-planning.yml`. Não edite arquivos em
`upstream/` por capricho — qualquer alteração ali é considerada um **patch
local** e deve seguir as regras abaixo.

## Versionamento

Formato: `MAJOR.MINOR.PATCH+upstream-X.Y.Z` (semver puro do wrapper +
build metadata identificando o snapshot do upstream vendorizado).

Veja [`CLAUDE.md`](../../CLAUDE.md) na raiz do marketplace para a tabela completa de bumps.

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

**Automático:** workflow `.github/workflows/sync-enhanced-planning.yml` roda
toda segunda-feira 09:00 UTC e abre PR se houver mudanças.

**Manual:**

```bash
gh workflow run sync-enhanced-planning.yml
```
