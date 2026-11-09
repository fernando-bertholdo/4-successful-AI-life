---
name: enhanced-planning
description: Adicionar guardrails estruturais a planos de implementacao. Use ao criar
  planos para milestones ou detours, quando o plano abrange multiplas sessoes, ou
  quando ha risco de drift entre componentes. Invoque ANTES de escrever o plano.
  Complementa (nao substitui) writing-plans.
---

# Enhanced Planning — Guardrails Estruturais para Planos

<!-- LOCAL-PATCH:start id=standalone-usage -->
## Standalone usage (fora do tech-product-template)

Este skill nasceu no `tech-product-template`, que tem um framework de planejamento
(initiatives → milestones/detours). Você **não** precisa desse framework para usar os guardrails:

- **milestone / detour / initiative** = a sua unidade de trabalho (uma feature, um épico, um fix).
  Onde o skill pede `enhanced-planning MX.X`, use qualquer rótulo: `enhanced-planning checkout-v2`.
- **`{{PLANNING_DIR}}`** = onde você guarda planos. Default sugerido: `.planning/` (ou `docs/plans/`).
  Se o seu projeto não tem esse diretório, salve o plano ao lado do código/PR.
- **Skills-companion opcionais** (`init-milestone`, `init-detour`, `validate-dor`, `validate-dod`,
  `archive-initiative`) pertencem ao framework de origem. Se você não os tem, **ignore** os passos
  que os mencionam — os guardrails funcionam sozinhos.
- As referências a `writing-plans` (superpowers) e a `/codex:rescue` (plugin Codex) são **reais** e
  recomendadas.
- A seção **"Mirror Upstream"** no fim do arquivo é metadado de manutenção do template — ignore como
  usuário do plugin.
<!-- LOCAL-PATCH:end id=standalone-usage -->

## Regra de Ouro

> "Todo plano de implementacao deve ter guardrails completos: checkpoints humanos, risk registry, decision locks, protocolo multi-sessao e, quando o `/codex:rescue` esta disponivel, o acesso existe e o usuário confirma, revisao Codex."

## Quando Usar

- Antes de criar plano para milestone ou detour
- Quando tarefa tem 3+ PRs/deliverables
- Quando plano abrange multiplas sessoes
- Quando slice toca output visivel ao stakeholder (email, report, dashboard)
- Quando ha risco de drift entre componentes

## Quando NAO Usar

- Tarefas simples (1-2 arquivos, <100 linhas)
- Correcoes pontuais sem risco de regressao, que nao alteram o plano
- Exploracao/pesquisa sem deliverable definido
- Quando `writing-plans` do superpowers ja foi invocado e a tarefa e trivial

## Parametros

```
enhanced-planning [milestone-id|detour-name]
```

**Exemplos:**
- `enhanced-planning MX.X` — Guardrails para milestone MX.X
- `enhanced-planning auth-refactor` — Guardrails para detour
- `enhanced-planning` — Guardrails sem initiative especifica

## Guardrails Incluidos

| Dimensao | Especificacao |
|----------|---------------|
| **Checkpoints humanos** | 6+ (por PR/fase) |
| **Continuidade multi-sessao** | Protocolo completo (tabela, CONTEXT.md, resume) |
| **Risk registry** | Completo (severidade, mitigacao, owner, status) |
| **Guardrails nomeados (G-*)** | Obrigatorio (selecionar do [catalogo](references/guardrail-catalog.md), verificacao por slice) |
| **Criterios de aceite** | Checkbox + comandos de verificacao + evidencia |
| **Verificacao cruzada docs** | Tabela de isonomia completa |
| **Revisao Codex** | Opcional: so entra com o `/codex:rescue` disponivel, a Checagem de Acesso passando e o usuário confirmando; por PR + meta-avaliacao via `/codex:rescue --effort xhigh` |
| **Decision locks** | Secao dedicada com tracking |
| **Verificacao final** | 10+ itens |
| **Sequencia de commits** | Tabela com PR + tipo + scope |

## Workflow

### Step 1 — Generate Planning Spec

Ler o template em [references/plan-template.md](references/plan-template.md).

**Secoes obrigatorias (exceto a 8, que e condicional):**

1. Contexto (problema + resultado esperado)
2. Implementacao (PRs com slices, arquivos, criterios de aceite)
3. Checkpoints Humanos (tabela: design, mid-point, final, desbloqueio, +por PR)
4. Guardrails Nomeados G-* (do [catalogo](references/guardrail-catalog.md))
5. Riscos e Mitigacoes (registry completo com severidade, owner, status)
6. Tabela de Progresso
7. Verificacao Cruzada / Isonomia Documental
8. Revisao Codex com meta-avaliacao (via `/codex:rescue`, do [protocolo](references/codex-review-protocol.md)) — **condicional**, ver abaixo
9. Decision Locks
10. Protocolo de Conclusao de PR (passos obrigatorios)
11. Protocolo Multi-Sessao
12. Sequencia de Commits
13. Verificacao Final (10+ itens)

> **A seção 8 é condicional.** Ao montar a Planning Spec, conferir antes a pré-condição de instalação do [protocolo](references/codex-review-protocol.md#quando-pular) (o `/codex:rescue` consta entre os comandos disponíveis na sessão) e, estando ela satisfeita, rodar a Checagem de Acesso do [protocolo](references/codex-review-protocol.md#checagem-de-acesso). Se a pré-condição falhar ou a Checagem sair com exit diferente de 0, omitir a seção 8 sem perguntar nada ao usuário e registrar `Revisao Codex: pulada ([motivo])`, com `plugin codex ausente` ou `sem acesso: ...` no lugar do motivo, numa nota logo abaixo da Tabela de Progresso (a tabela é por slice e não tem linha para um pulo do plano). Se as duas passarem, a seção 8 só entra depois da confirmação do usuário no Step 2.

**Output:** Planning Spec — documento intermediario com:
1. Lista de secoes obrigatorias
2. Guardrails G-* ativos
3. Checkpoints humanos com momentos definidos
4. Template de cada secao pre-preenchido com placeholders

### Step 2 — CHECKPOINT HUMANO: Confirmar Guardrails

> Usar AskUserQuestion para apresentar ao usuario:
> 1. Secoes obrigatorias que serao incluidas no plano
> 2. Guardrails G-* ativos
> 3. Checkpoints humanos planejados
>
> Perguntar: "Os guardrails estao adequados para a tarefa?
> Opcoes: (A) Confirmar e prosseguir, (B) Adicionar/remover guardrails especificos."

**Revisão Codex — confirmar com o usuário antes de pô-la no plano.** A skill pode acrescentá-la a qualquer plano que nasça dela, complexo ou não, e a revisão gasta a cota do Codex do usuário. A Checagem de Acesso, que roda antes desta pergunta, faz uma chamada mínima ao serviço, também a gasta e deixa uma sessão gravada em `~/.codex/sessions` (ver o protocolo), mesmo que o usuário recuse a seção 8: é o preço de não perguntar por uma revisão que não rodaria. Quando a pré-condição de instalação e a Checagem de Acesso passaram, perguntar à parte, em outro AskUserQuestion:

> "O acesso ao Codex foi confirmado. Incluir a revisao Codex neste plano?
> Opcoes: (A) Incluir, (B) Nao incluir — a secao 8 sai do plano e o pulo e registrado numa nota logo abaixo da Tabela de Progresso."

Sem resposta (A), a seção 8 não entra.

### Step 3 — Inject into Plan

Inserir a Planning Spec como requisitos estruturais no plano.

**A seção 8 é condicional nos dois ramos abaixo.** Quando a pré-condição de instalação ou a Checagem de Acesso falhou, ou o usuário não confirmou no Step 2, a secao "Revisao Codex" (e o item correspondente da Verificacao Final) fica fora do plano, e o pulo e registrado como no Step 1. As demais secoes obrigatorias continuam obrigatorias.

**Se usando `writing-plans` (superpowers):**
- A Planning Spec funciona como pre-requisito estrutural
- O agente deve incluir TODAS as secoes obrigatorias no plano gerado, exceto a 8 quando a regra acima a deixou de fora
- Checkpoints humanos devem usar AskUserQuestion nos momentos definidos

**Se criando plano diretamente:**
- Usar o template de [plan-template.md](references/plan-template.md) como esqueleto
- Preencher com conteudo especifico da tarefa
- Garantir que nenhuma secao obrigatoria foi omitida, salvo a 8 pela regra acima
- Remover do esqueleto a secao "Revisao Codex" (e o item correspondente da Verificacao Final) quando a regra acima a deixou de fora

### Step 4 — Validate Plan Completeness

Apos o plano ser escrito, validar os checks da lista abaixo:

- [ ] Secao Contexto presente com problema + resultado esperado
- [ ] Checkpoints humanos definidos (minimo: design, mid-point, final)
- [ ] Guardrails G-* listados com descricao de aplicacao
- [ ] Registro de riscos presente com pelo menos 1 risco (severidade + owner)
- [ ] Tabela de progresso presente (vazia, pronta para preencher; o pulo da revisao Codex, se houve, fica numa nota logo abaixo dela)
- [ ] Protocolo de Conclusao de PR presente com passos obrigatorios (checkboxes, tabela, CONTEXT.md)
- [ ] CONTEXT.md referenciado como destino do diario de rodadas
- [ ] Revisao Codex: se o usuário confirmou, secao presente com meta-avaliacao referenciada (via `/codex:rescue`); senao, secao ausente e pulo registrado na nota abaixo da Tabela de Progresso
- [ ] Decision locks documentados
- [ ] Tabela de isonomia documental presente
- [ ] Protocolo multi-sessao com 4 regras (inclui atualizacao obrigatoria de CONTEXT.md)
- [ ] Sequencia de commits planejada
- [ ] Verificacao final com 10+ itens (inclui CONTEXT.md)

Se validacao falhar, informar quais secoes estao faltando e sugerir correcoes.

## Integracao com Skills Existentes

| Skill | Relacao com enhanced-planning |
|---|---|
| `writing-plans` (superpowers) | enhanced-planning gera spec ANTES; writing-plans preenche conteudo DEPOIS |
| `validate-dor` | Usar ANTES de enhanced-planning para validar pre-requisitos do milestone |
| `validate-dod` | Usar DEPOIS da implementacao para validar completude |
| `fresh-context` | Invocar nos pause points definidos pelo protocolo multi-sessao |
| `organize-commits` | Seguir sequencia de commits definida no plano |
| `init-milestone` | Invocar ANTES de enhanced-planning para criar infraestrutura (milestones) |
| `init-detour` | Invocar ANTES de enhanced-planning para criar infraestrutura (detours) |
| `agent-team` | Compativel — plano com guardrails pode ser executado por equipe |

## Fluxo Completo

```
[1] init-milestone MX.X | init-detour <nome>  (criar infra)
[2] validate-dor MX.X | <nome>               (validar pre-requisitos)
[3] enhanced-planning MX.X | <nome>          (definir guardrails)    <-- ESTA SKILL
[4] writing-plans / plano direto              (escrever plano COM guardrails)
[5] implementar slices                        (seguir plano)
[6] validate-dod MX.X | <nome>               (validar completude)
```

## Plan Lifecycle (Criacao → Commit → Arquivamento)

Planos gerados por esta skill ou pelo `writing-plans` do superpowers tem ciclo de vida definido. A regra central e: **planos sao artefatos de trabalho, nao documentacao permanente**.

### Tipos de artefato de plano

| Origem | Diretorio | Lifecycle | Exemplo |
|--------|-----------|-----------|---------|
| `enhanced-planning` / `writing-plans` | `.claude/superpowers/plans/` | Commit ao criar → Archive ao concluir | `2026-03-23-feature-x.md` |
| `brainstorming` (design specs) | `.claude/superpowers/specs/` | Commit ao criar → Archive ao concluir | `2026-03-22-feature-x-design.md` |
| Plan mode (Claude Code) | `.claude/plans/` | **Gitignored** — efemero, nao commitar | `cuddly-inventing-panda.md` |

### Na criacao do plano

1. **Salvar** o plano no diretorio de superpowers (ou `{{PLANNING_DIR}}<initiative>/plans/` se preferir co-localizar)
2. **Commitar** como parte do setup do milestone/detour:
   ```
   chore(planning): adiciona plano de implementacao para [initiative-id]
   ```
3. **Registrar** referencia no CONTEXT.md da initiative (se existir)

### Durante a execucao

- O plano e a referencia viva — atualizar tabela de progresso, checkboxes, decision locks
- Commitar atualizacoes de progresso junto com os slices (nao em commits separados)

### Na conclusao (pos-DoD)

Quando `validate-dod` retornar PASS e `archive-initiative` for invocado:

1. **Planos em `.claude/superpowers/`:** `archive-initiative` move para `_archive/<initiative>/plans/`
2. **Planos ja co-localizados em `{{PLANNING_DIR}}<initiative>/plans/`:** movidos automaticamente com o diretorio pai
3. **Plan mode (`.claude/plans/`):** ja gitignored — deletar localmente se desejado

### Limpeza periodica

Se planos se acumularem sem initiative associada:
- Verificar se foram implementados (cruzar com git log)
- Se implementados → deletar (codigo e commits sao a fonte de verdade)
- Se parcialmente implementados → mover para `{{PLANNING_DIR}}detours/<nome>/plans/` ou `{{PLANNING_DIR}}scratch/`
- Se obsoletos → deletar

> **Regra:** Planos executados nao sao documentacao. O codigo, os commits e os docs core sao a fonte de verdade pos-implementacao.

---

## Mirror Upstream

Esta skill usa placeholders para neutralizacao ao exportar para templates:

| Placeholder | Descricao |
|---|---|
| `{{PROJECT_NAME}}` | Nome do projeto |
| `{{CODEX_MODEL}}` | Modelo Codex para revisao |
| `{{PLANNING_DIR}}` | Diretorio de planning |
| `{{DOCS_DIR}}` | Diretorio de docs core |

Ao executar `mirror-upstream`, substituir valores concretos por placeholders.

---

**Versao:** 2.1.1
**Ultima atualizacao:** 01/Outubro/2026
**Autor:** Fernando Bertholdo

## Changelog

### v2.1.1 (01/Outubro/2026)
- Aparas da revisao da TECH-830 (TECH-907): a secao 8 deixa de constar como obrigatoria nos dois ramos do Step 3 (`writing-plans` e plano direto), com o carve-out antes da bifurcacao; o pulo do plano vai numa nota abaixo da Tabela de Progresso e o de um PR na coluna Notas; o Step 4 deixa de contar os checks; o texto assume que a Checagem gasta uma chamada antes da pergunta
- Protocolo Codex: a Checagem fecha o stdin (`</dev/null`) e pula tambem no estouro de tempo; o `/codex:setup` vira pre-condicao de instalacao, fora da decisao de acesso; o medido fica separado do esperado; a flag `--skip-codex`, que a skill nao declara, sai
- Rodada 2 do PR #57 (TECH-907): a opcao (B) do Step 2 aponta a nota abaixo da Tabela de Progresso; o plan-template ressalva a Revisao Codex na abertura; o Step 1 e o Step 2 so perguntam pela revisao com o `/codex:rescue` disponivel na sessao (pre-condicao conferida antes da Checagem, motivo `plugin codex ausente`); o protocolo cita o `ready` do `/codex:setup` por simbolo e declara o rastro de sessao da Checagem
- Rodada 3 do PR #57 (TECH-907): o passo 3 de "Ao completar cada PR" e a faixa da secao 8 do plan-template conferem a presenca do `/codex:rescue`; a contagem das condicoes de pular passa a tres (a pre-condicao de instalacao vira bullet de "Quando Pular") no protocolo, na tabela da skill e na Regra de Ouro

### v2.1.0 (01/Outubro/2026)
- A revisao Codex deixa de ser secao obrigatoria: so entra no plano com a Checagem de Acesso do protocolo passando e o usuário confirmando no Step 2 (TECH-830)
- A condicao de pular testa o acesso (`codex exec`), nao o binario: `codex --version` saía com exit 0 mesmo com o acesso negado, e o plano trazia uma revisão que quebrava no meio (medicao da TECH-830, 30/09/2026)

### v2.0.0 (24/Marco/2026)
- **BREAKING:** Remove sistema de 3 tiers (LOW/MEDIUM/HIGH) — agora existe um unico modo equivalente ao antigo HIGH
- Remove Step "Tier Assessment" (scoring, classificacao) — nao ha mais selecao de tier
- Remove Tier Comparison Matrix
- Parametros simplificados: `enhanced-planning [initiative-id]` (sem tier)
- Template unico em `plan-template.md` (substitui `tier-templates.md`)
- Codex Review Protocol simplificado (sempre por PR + meta-avaliacao, effort xhigh)
- Workflow reduzido de 5 para 4 steps
- Validacao unificada em 10+ checks (sem separacao por tier)

### v1.1.0 (23/Marco/2026)
- Adiciona secao "Plan Lifecycle" com regras para commit, co-localizacao, e arquivamento de planos

### v1.0.0 (20/Marco/2026)
- Criacao inicial: workflow 5-step, tier matrix, auto-assessment, integracao com skills existentes

<!-- @runtime-placeholders: CODEX_MODEL, DOCS_DIR, PLANNING_DIR, PROJECT_NAME -->
