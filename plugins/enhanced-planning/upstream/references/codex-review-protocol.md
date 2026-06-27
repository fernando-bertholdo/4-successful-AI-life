# Codex Review Protocol

Protocolo de revisao cruzada Codex em 2 fases. Executar **1 revisao por PR/deliverable** com meta-avaliacao.

## Como Invocar

**A revisao Codex DEVE ser executada via `/codex:rescue`.** Invocar antes de montar o prompt, passando `--effort xhigh` na chamada.

**Effort recomendado:** passar a flag `--effort xhigh` ao invocar `/codex:rescue`.

> Exemplo de fluxo: ao chegar no passo "Invocar Codex", o agente deve chamar `/codex:rescue --effort xhigh` com o prompt abaixo e aguardar o resultado.

## Pre-requisitos

- PR/deliverable com criterios de aceite 100% marcados
- Verificacao cruzada de docs completa
- Codex CLI disponivel no ambiente (verificar `codex --version` antes de invocar)

## Protocolo de 2 Fases

### Fase 1 — Exploracao Independente

**Objetivo:** Codex explora o codebase SEM ver os criterios de aceite. Avalia qualidade do que foi implementado de forma independente.

**Execucao:** Invocar `/codex:rescue --effort xhigh` com o prompt abaixo.

**Prompt template:**
```
Explore o codebase e avalie o que foi implementado nos slices [SLICE_IDS]
(PR-[PR_ID] do plano `.claude/plans/[PLAN_FILE]`).

Analise os arquivos criados/modificados: [FILE_LIST].

Identifique:
- Gaps entre planejado e implementado
- Riscos nao cobertos por testes
- Problemas de qualidade ou completude
- Inconsistencias entre componentes
```

### Fase 2 — Classificacao Comparativa

**Objetivo:** Codex compara achados da Fase 1 com o plano e classifica severidade.

**Execucao:** Continuar a sessao Codex anterior via `/codex:rescue --resume`, enviando o prompt abaixo.

**Prompt template:**
```
Compare suas conclusoes com o plano original em `.claude/plans/[PLAN_FILE]`,
especificamente a secao do PR-[PR_ID].

Classifique cada achado como:
- CRITICO: bloqueia qualidade/corretude — deve ser corrigido antes de avancar
- MEDIO: melhoria relevante mas nao bloqueadora — pode ser ajustado no PR atual ou posterior
- BAIXO: cosmetico/opcional — registrar como observacao
```

## Meta-Avaliacao Claude

Apos retorno do Codex, o agente Claude avalia os achados:

| Severidade | Acao |
|---|---|
| CRITICO | Corrigir antes de avancar ao proximo PR. Se nao for possivel, abrir item no backlog. |
| MEDIO | Propor ajuste ao plano (secao do PR atual ou posterior). Registrar como melhoria opcional se rejeitado. |
| BAIXO | Registrar como observacao sem acao imediata. |
| Sem achados | Registrar `Revisao Codex PR-[N]: sem ajustes necessarios` |

## Registro

Resultado DEVE ser registrado em dois locais:
1. **Tabela de Progresso** do plano (coluna Notas)
2. **Criterios de aceite** do PR (adicionar linha com resultado)

**Formato:**
```
Revisao Codex PR-[N]: [X] CRITICO(s), [Y] MEDIO(s), [Z] BAIXO(s).
[Resumo de 1 linha dos achados principais]
```

## Quando Pular

A revisao Codex pode ser pulada se:
- Usuario explicitamente opta por pular (`--skip-codex`)
- Codex CLI nao esta disponivel no ambiente (`codex --version` falha)
- Plugin `codex` nao esta instalado (verificar com `/codex:setup`)

Registrar pulo na Tabela de Progresso: `Revisao Codex: pulada ([motivo])`
