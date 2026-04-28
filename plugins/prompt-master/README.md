# prompt-master (vendored)

Wrapper de plugin Claude Code que vendoriza o skill [`nidhinjs/prompt-master`](https://github.com/nidhinjs/prompt-master) e o distribui via este marketplace.

## Origem

- **Upstream:** https://github.com/nidhinjs/prompt-master
- **Autor original:** Nidhin Joseph Nelson
- **Licença upstream:** MIT (preservada em `upstream/LICENSE`)

O conteúdo do skill (incluindo `SKILL.md` e `references/`) vive em `upstream/` e é puxado via `git subtree`. Não edite arquivos em `upstream/` por capricho — qualquer alteração ali é considerada um **patch local** e deve seguir as regras abaixo.

## Versionamento

Formato: `MAJOR.MINOR.PATCH+upstream-X.Y.Z`

- A parte antes do `+` segue semver puro do *nosso* wrapper (mudanças nossas).
- A parte depois do `+` é metadata indicando qual versão do upstream foi vendorizada.

| Mudança | Bump |
|---|---|
| Sync upstream (sem alterar patches) | só `+upstream-X.Y.Z` |
| Adição de patch local que altera comportamento | MINOR |
| Correção de patch local | PATCH |
| Refator de patches por breaking change do upstream | MAJOR |

## Patches locais

Edite arquivos em `upstream/` diretamente, mas **sempre** delimite o bloco com sentinelas:

```markdown
<!-- LOCAL-PATCH:start id=identificador-curto -->
... seu conteúdo ...
<!-- LOCAL-PATCH:end id=identificador-curto -->
```

Documente cada patch no `CHANGELOG.md` deste diretório (separado do CHANGELOG do upstream). Quando um `git subtree pull` der conflito, esses sentinelas facilitam encontrar e re-aplicar.

## Sync com upstream

**Automático:** workflow `.github/workflows/sync-prompt-master.yml` roda toda segunda-feira às 09:00 UTC e abre PR se houver mudanças.

**Manual:**

```bash
git subtree pull --prefix=plugins/prompt-master/upstream \
  https://github.com/nidhinjs/prompt-master.git main --squash
```
