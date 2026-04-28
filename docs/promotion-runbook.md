# Promotion Runbook

Como promover uma skill do `tech-product-template` (privado) para este marketplace (público), com sync automático.

## Modelo arquitetural

```
┌─────────────────────────────────────────────────────────┐
│  Tier 1 — tech-product-template (privado)               │
│  Fonte de verdade. Tudo nasce aqui. Coupling permitido. │
│  Vocabulário próprio (initiative, milestone, detour).   │
└──────────────────────┬──────────────────────────────────┘
                       │ promoção (manual, só skills maduras)
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Tier 2 — 4-successful-AI-life (público)                │
│  Distribuição. Só recebe peças prontas para terceiros.  │
│  Skills agnósticas standalone OU bundles coesos.        │
└─────────────────────────────────────────────────────────┘
```

**Movimento é sempre Tier 1 → Tier 2.** Nunca o inverso. Skills nascem e evoluem no template; o marketplace recebe snapshots vendorizados via subtree/sparse-checkout, com sync automático apontando de volta para o template.

## Setup one-time (antes da primeira promoção)

### Passo 1 — Criar fine-grained PAT

Necessário porque o `GITHUB_TOKEN` padrão dos workflows só autentica contra o **próprio** repo. Para clonar `tech-product-template` (que é privado), precisamos de um token externo.

1. Vá em https://github.com/settings/personal-access-tokens
2. Clique em **Generate new token** → **Fine-grained personal access token**
3. Configure:
   - **Token name:** `marketplace-sync-template-readonly`
   - **Expiration:** 1 ano (máximo permitido em fine-grained PATs — anote no calendário pra rotacionar)
   - **Repository access:** Only select repositories → `fernando-bertholdo/tech-product-template`
   - **Repository permissions:** Apenas `Contents: Read` (nada mais — princípio do menor privilégio)
4. Generate → copie o token (formato `github_pat_...`). **Você não verá ele de novo.**

### Passo 2 — Adicionar como secret no marketplace

```bash
gh secret set UPSTREAM_TOKEN --repo fernando-bertholdo/4-successful-AI-life
# cola o token quando pedir
```

Ou via UI: https://github.com/fernando-bertholdo/4-successful-AI-life/settings/secrets/actions → New repository secret → Name: `UPSTREAM_TOKEN`, Value: `github_pat_...`

### Passo 3 — Verificar

```bash
gh secret list --repo fernando-bertholdo/4-successful-AI-life
# UPSTREAM_TOKEN deve aparecer
```

## Promovendo uma skill

```bash
scripts/promote-skill.sh <skill-name>
```

Exemplo:

```bash
scripts/promote-skill.sh organize-commits
```

O script:

1. Valida que a skill existe em `~/Documents/tech_projects/tech-product-template/.claude/skills/<name>/`
2. Cria `plugins/<name>/upstream/` com cópia inicial
3. Gera `plugin.json`, `README.md`, `CHANGELOG.md` do wrapper
4. Cria `.github/workflows/sync-<name>.yml` (trigger fininho que delega ao reusable)
5. Imprime entrada sugerida pra colar no `marketplace.json`

Você ainda precisa, manualmente:

- Colar entrada no `.claude-plugin/marketplace.json` (e bumpar versão do marketplace)
- Atualizar `CHANGELOG.md` raiz
- Revisar conteúdo, commitar, abrir PR
- Mergear com `--merge` (nunca squash — quebra rastreabilidade)

## Regras inegociáveis

### Sempre `--merge`, nunca `--squash`

Squash colapsa commits em um só, perdendo o `chore(...): sync from ...` que documenta cada snapshot vendorizado. A rastreabilidade do "qual versão do upstream estava embebida em qual commit nosso" depende desse histórico.

### Patches locais sempre com sentinelas

```markdown
<!-- LOCAL-PATCH:start id=identificador-curto -->
... seu conteúdo ...
<!-- LOCAL-PATCH:end id=identificador-curto -->
```

Sem sentinela, conflitos em sync futuros viram pesadelo.

### Versionamento

Formato: `MAJOR.MINOR.PATCH+upstream-X.Y.Z`

| Cenário | Bump |
|---|---|
| Sync upstream (sem alterar patches) | só `+upstream-X.Y.Z` |
| Patch local que altera comportamento | MINOR |
| Correção de patch local | PATCH |
| Refator de patches por breaking change do upstream | MAJOR |

A parte antes do `+` é semver puro do **wrapper** (nosso código). A parte depois do `+` é build metadata identificando o snapshot do upstream.

## Critério de promoção

Antes de promover, valide:

- [ ] A skill funciona em projetos sem `.planning/` / sem o framework do template (ou tem fallback gracioso via sentinelas de modo)
- [ ] O `SKILL.md` não referencia skills do template que não existem fora dele
- [ ] O vocabulário do output é compreensível por quem não conhece o template
- [ ] A skill tem valor standalone (alguém escolheria instalar **só ela** sem nem conhecer o template)

Se algum destes itens falhar, ela ainda não está pronta para promoção — refatore no template primeiro.

## Rotação de PAT

Anote no calendário 11 meses após criar a PAT (GitHub avisa por email 1 semana antes). Quando expirar:

1. Crie nova PAT seguindo o Passo 1 acima
2. `gh secret set UPSTREAM_TOKEN --repo fernando-bertholdo/4-successful-AI-life`
3. Delete a PAT antiga em https://github.com/settings/personal-access-tokens

## Troubleshooting

**Workflow falha com "fatal: could not read Username for 'https://github.com'"**
→ PAT não configurada ou inválida. Recheque o secret `UPSTREAM_TOKEN`.

**Workflow falha com "remote: Repository not found"**
→ A PAT não tem acesso ao `tech-product-template`. Recheque a permissão `Contents: Read` no escopo da PAT.

**PR de sync nunca aparece mas o workflow roda verde**
→ É esperado quando o upstream não mudou desde a última sync. Cheque os logs: deve dizer "Nenhuma mudança em ... desde a última sync."

**Sync gerou conflitos em arquivos com `LOCAL-PATCH`**
→ O upstream mexeu numa região próxima ao seu patch. Resolva o conflito manualmente no PR antes de mergear, preservando os blocos `LOCAL-PATCH:start`...`LOCAL-PATCH:end`.
