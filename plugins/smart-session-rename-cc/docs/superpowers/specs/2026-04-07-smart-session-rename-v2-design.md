# Smart Session Rename v2 — Design Spec (progressão da v1.5)

**Data original:** 2026-04-07
**Reenquadrado em:** 2026-04-14 (após decisão de construir a v1.5 primeiro)
**Autor:** Fernando + Claude
**Status:** Design aprovado conceitualmente; **execução contingente** à adoção e valor percebido da v1.5 em uso real
**Versão:** 2.0
**Baseline:** [v1.5 design](./2026-04-14-smart-session-rename-v15-design.md)

---

## 1. Contexto e motivação

Esta spec descreve a **evolução cognitiva** da v1.5. A v1.5 resolveu o problema estrutural de economia de chamadas LLM em modo OAuth (custo real ~$0.10/chamada) com heurísticas determinísticas de throttling + uma única chamada LLM com structured output garantido. A v1.5 entrega o valor central (formato `domain: clauses`, evolução incremental, controles manuais) a um custo previsível de ~$0.60/sessão.

A v2 é sobre **adicionar inteligência sobre a base da v1.5**: pedir à LLM não apenas "como chamar" mas "o que mudou" e "que tipo de sessão é essa", permitindo decisões cognitivas mais finas (classificar intenção, distinguir tipos de sessão, reagrupar cláusulas quando ficam confusas, detectar pivots).

**Critério de decisão para construir a v2:** após 4-8 semanas de uso real da v1.5, avaliar se:
1. O plugin está sendo usado regularmente (não foi desabilitado por ruído ou custo)
2. Os títulos gerados ajudam de fato no dia-a-dia (medida subjetiva)
3. Há lacunas identificadas que justificam sofisticação adicional
4. O custo adicional de uma segunda camada de LLM (~+50%) é aceitável

Se pelo menos 3 dos 4 critérios forem sim, vale iniciar o trabalho de v2.

## 2. O que a v2 adiciona sobre a v1.5

Os itens abaixo estão registrados em `memory/project_v2_deferred.md` como "cortes conscientes da v1.5":

1. **Arquitetura de 2 camadas LLM** — Triage (classifica intenção) → Generation (gera título). A Camada 1 é barata (~150-200 tokens) e decide se Camada 2 precisa rodar. Reduz custo em sessões onde a maioria dos turnos não muda nada substancial.

2. **Classificação de `session_kind`** — `feature_work | bugfix | exploration | qa_session | review`. O render do título varia por tipo: sessões exploratórias ganham título tipo `exploring: <tema>` em vez de acumular cláusulas como uma feature.

3. **Reagrupamento automático (`regrouped`)** — quando acumulam muitas cláusulas e o título fica ilegível, a Camada 2 consolida em um conceito guarda-chuva (ex: 5 cláusulas de segurança → `auth hardening`). Usa retry de prompt se a LLM não regrupou na primeira tentativa.

4. **Ação `rollback` via triage** — quando o usuário volta a um foco anterior, a Camada 1 detecta e restaura um título do histórico em vez de gerar um novo.

5. **`transition_history` completo** — inclui keeps, refinements e rollbacks com razões. Habilita análises retrospectivas e futuro `/smart-rename replay`.

6. **Circuit breakers duplos** — um por camada. Falha persistente na Camada 1 desabilita triage (e todos os turnos vão direto para Camada 2 ou keep). Falha persistente na Camada 2 desabilita geração (só Camada 1 + re-anexação).

7. **Análises cross-sessão** — subcomandos como `/smart-rename stats` (custos, frequência de CALLs, taxa de keep, sessões mais caras) e `/smart-rename replay <turno>` (re-roda uma decisão antiga com prompt atualizado para comparar).

8. **Suporte a múltiplos modelos** — Sonnet para sessões onde a qualidade precisa ser alta (ex: configurável via env var), Haiku por default.

9. **Garbage collection de `custom-title`** — remove registros antigos do JSONL em sessões gigantes (>500 turnos) para não inflar o arquivo.

10. **Possível migração para Node.js** — se a complexidade da Camada 2 + retry + validação rica + gestão de state + stats se tornar pesada demais em bash, reescrever a lógica em Node.js (mantendo hook shell mínimo). Decisão contingente.

---

## 3. Arquitetura da v2 (delta sobre a v1.5)

### 3.1 Novo fluxo por turno

```
Stop hook dispara
        │
        ▼
┌──────────────────────────┐
│ Passos 1-3 da v1.5       │  ← inalterados
│ (config, state, detect   │
│  /rename, parse transcript)│
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│ 4. work_score + guards   │  ← **modificado na v2**
│    decidem: chamar a     │     Em vez de ir direto para Camada 2,
│    pipeline cognitiva?   │     vai para Camada 1 (triage) primeiro
└──────────────────────────┘
        │ sim
        ▼
┌──────────────────────────┐
│ 5. Camada 1 — Triage     │  ← **novo**
│    Haiku (~150-200 tkn)  │
│    retorna:              │
│    {action: keep|extend  │
│          |refine|rollback│
│          |pivot, reason} │
└──────────────────────────┘
        │
        ├─ keep ────────────► re-anexa título, log, sai
        │
        │ extend/refine/rollback/pivot
        ▼
┌──────────────────────────┐
│ 6. Camada 2 — Generation │  ← **modificado na v2**
│    Haiku (~400-500 tkn)  │     Agora retorna JSON rico:
│    com regroup se precisa│     {domain, clauses, regrouped,
│                          │      session_kind, confidence,
│                          │      next_summary}
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│ 7. Validate + render     │  ← **ampliado na v2**
│    com branches para     │     session_kind e regrouped mudam
│    session_kind + regroup│     o formato final
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│ 8. Escreve, log, unlock  │  ← inalterado da v1.5
└──────────────────────────┘
```

### 3.2 Módulos novos ou modificados (aditivo sobre v1.5)

| Módulo | Status | Responsabilidade |
|---|---|---|
| `scripts/lib/triage.sh` | **novo** | Chamada LLM da Camada 1 + parsing + validação |
| `scripts/lib/generate.sh` | **novo** (absorve parte do v1.5 `llm.sh`) | Camada 2 + retry de regroup + validação rica |
| `scripts/lib/validate.sh` | **ampliado** | Render com branches de session_kind e regrouped |
| `scripts/lib/scorer.sh` | **modificado** | Decide pipeline cognitiva, não mais "call direct" |
| `scripts/lib/llm.sh` | **transformado em helper** | Apenas wrapper genérico de `claude -p`, chamado por triage.sh e generate.sh |
| `prompts/v2/triage.md` | **novo** | Prompt da Camada 1 |
| `prompts/v2/generation.md` | **novo** (evolução de `prompts/generation.md` da v1.5) | Prompt da Camada 2 |
| `prompts/v2/generation-regroup.md` | **novo** | Variante usada no retry de reagrupamento |

### 3.3 Coexistência v1.5 ↔ v2

Padrão igual ao que a v1.5 usou para substituir a v1 (sem roteador), mas agora com a diferença de que a v2 **adiciona** módulos, não substitui. O hook detecta via config qual pipeline usar:

```bash
# rename-hook.sh
if [ "$(config_get pipeline)" = "v2" ]; then
  v2_pipeline
else
  v15_pipeline  # default
fi
```

Config: `SMART_RENAME_PIPELINE=v2` ativa a pipeline cognitiva. Default continua `v15`.

### 3.4 Migração de estado v1.5 → v2

Estado v1.5 é reconhecido por `version: "1.5"`. Migração adiciona campos novos sem remover nada:

- Adiciona `title_struct.regrouped: false`, `title_struct.regrouped_as: null`
- Adiciona `session_kind: null` (será preenchido pela Camada 2 na primeira chamada v2)
- Amplia `transition_history` permitindo mais itens (novo cap configurável, default 10)
- Adiciona `failure_stats: {layer_1_fails, layer_2_fails, layer_1_disabled, layer_2_disabled}`
- Preserva `failure_count` + `llm_disabled` da v1.5 como compatibilidade (ou renomeia para `layer_2_*`)
- `version` → `"2"`

Não há rollback automático de v2 → v1.5; se usuário desabilitar pipeline v2, o estado v2 é tratado como estendido mas compatível pela v1.5.

---

## 4. Camada 1 — Triage

### 4.1 Pré-filtro determinístico (herdado + melhorado)

A v1.5 já tem o `scorer.sh` como pré-filtro dominante. A v2 adiciona um pré-filtro mais fino **antes** da Camada 1:

- Zero tool calls no turno atual
- Mensagem do usuário ≤ 3 palavras
- Soma de frases do assistente ≤ 2

Se todas as três, triage retorna `keep` sem chamar LLM. Elimina 20-30% de chamadas em sessões conversacionais.

### 4.2 Chamada LLM (Camada 1)

Prompt enxuto com:
- Título renderizado atual e estrutura JSON
- Resumo do estado vivo (session_kind, domain_guess, top 5 active_files, last_summary)
- Primeira frase da msg do usuário do turno (≤500 chars)
- Primeira frase do último text block do assistente (≤500 chars)
- Últimas 3 entradas do transition_history

Categorias de retorno: `keep | extend | refine | rollback | pivot`

Output:
```json
{"action": "extend", "reason": "novo trabalho de segurança adicionado"}
```

Tamanho: ~150-200 tokens prompt + ~20 tokens output. Custo estimado em modo `--bare` (com API key): ~$0.0001. Em modo OAuth: ~$0.08 (limitação do spec v2, herdada da realidade empírica da v1.5).

**Nota de custo:** mesmo em OAuth, a Camada 1 pode valer se 70%+ dos turnos resultarem em `keep` (evita a Camada 2 mais cara). Em sessões muito ativas, triage pode acabar sendo desperdício. A decisão de ativar v2 deve ser empírica.

### 4.3 Pós-processamento

- `keep` → re-anexa título atual, registra no log, sai
- `rollback` → consulta `transition_history`, passa Camada 2 com `rollback_target`
- `extend | refine | pivot` → chama Camada 2 com `action + reason` no contexto

### 4.4 Fallback

Falha na Camada 1 → assume `keep`, incrementa `layer_1_fails`. Circuit breaker desabilita triage após 5 falhas consecutivas.

---

## 5. Camada 2 — Generation (evolução do LLM da v1.5)

### 5.1 Quando roda

- Camada 1 retorna `extend | refine | rollback | pivot`
- Bypass: primeira nomeação da sessão, `/smart-rename force`, sessão migrada de v1.5 sem `session_kind` ainda classificado

### 5.2 Inputs do prompt

- `title_struct` atual (domain + clauses)
- Resultado da Camada 1 (action + reason)
- Estado vivo completo (session_kind, domain_guess, top 10 active_files, last_summary, branch, cwd)
- Últimos 3 pares user/assistant
- `transition_history` (últimas 5 entradas)
- `manual_anchor` e `rollback_target` se aplicáveis

### 5.3 Output esperado (JSON rico)

```json
{
  "domain": "auth",
  "clauses": ["fix jwt expiry", "add tests", "rate limit endpoints"],
  "regrouped": false,
  "regrouped_as": null,
  "pivot_detected": false,
  "confidence": 0.92,
  "session_kind": "feature_work",
  "next_summary": "Hardening do módulo de auth: JWT, testes, rate limiting"
}
```

### 5.4 Validação e regras

Além das validações da v1.5:

- `pivot_detected: false` + `domain != state.title_struct.domain` → **rejeita** output (guardrail de consistência); mantém título, log warning, não conta como falha de circuit breaker.
- `regrouped: true` exige `regrouped_as` não vazio.
- `clauses.length > max_clauses_before_regroup (7)` + `regrouped: false` → retry com `prompts/v2/generation-regroup.md`.
- Até 2 tentativas totais.

### 5.5 Render com branches

```
se manual_anchor: "{anchor} · {clauses.join(', ')}"
senão se regrouped: "{domain}: {regrouped_as}"
senão se session_kind == "exploration": "exploring: {clauses.join(', ')}"
senão se session_kind == "qa_session": "q&a: {clauses.join(', ')}"
senão: "{domain}: {clauses.join(', ')}"
```

### 5.6 Fallback

Falha na Camada 2 → mantém título atual, incrementa `layer_2_fails`. Circuit breaker desabilita após 5 falhas. Reset com sucesso.

---

## 6. Estado v2 (extensão do v1.5)

Campos **novos** sobre o schema v1.5:

```json
{
  "version": "2",
  "title_struct": {
    "domain": "auth",
    "clauses": [...],
    "regrouped": false,           // novo
    "regrouped_as": null           // novo
  },
  "session_kind": "feature_work", // novo
  "last_summary": "...",           // novo
  "last_summary_turn": 7,          // novo
  "last_layer_2_turn": 7,          // novo
  "failure_stats": {               // substitui failure_count + llm_disabled da v1.5
    "layer_1_fails": 0,
    "layer_2_fails": 0,
    "layer_1_disabled": false,
    "layer_2_disabled": false,
    "degraded_turns": 0
  },
  "migrated_from_v15": true        // flag de migração
}
```

Campos **inalterados** herdados da v1.5: `rendered_title`, `last_plugin_written_title`, `manual_anchor`, `frozen`, `force_next`, `accumulated_score`, `calls_made`, `overflow_used`, `last_processed_turn`, `domain_guess`, `active_files_recent`, `branch`, `transition_history`, `created_at`, `updated_at`.

### 6.1 Idempotência e locking

Herdados da v1.5 sem mudança.

### 6.2 Atomicidade

Herdada da v1.5 sem mudança.

---

## 7. Skill — Subcomandos adicionais da v2

Sobre os 7 da v1.5, a v2 adiciona:

| Comando | Efeito |
|---|---|
| `/smart-rename stats` | Mostra sumário agregado: total de sessões, custo total, taxa keep/extend/refine/pivot, sessões mais caras |
| `/smart-rename replay <turno>` | Re-roda a decisão de um turno antigo com o prompt atual (comparação de regressão) |
| `/smart-rename classify` | Força reavaliação do `session_kind` atual |

---

## 8. Logs e observabilidade (extensão)

Eventos novos na v2:

- `layer_1_call_start`, `layer_1_call_end`, `layer_1_decision`
- `layer_2_call_start`, `layer_2_call_end`, `layer_2_retry_regroup`
- `layer_2_guardrail_rejected` (com `guardrail: string`)
- `session_kind_classified`
- `layer_N_circuit_breaker_tripped`
- `stats_computed`, `replay_executed`

---

## 9. Configuração (extensão)

Sobre a v1.5:

```json
{
  "pipeline": "v15",
  "triage_enabled": true,
  "pre_filter_trivial_turns": true,
  "max_clauses_before_regroup": 7,
  "max_clauses_hard_limit": 12,
  "layer_1_failure_threshold": 5,
  "layer_2_failure_threshold": 5,
  "transition_history_cap": 10,
  "allow_model_override": false,
  "override_model_for_generation": "claude-sonnet-4-6"
}
```

Env vars: `SMART_RENAME_PIPELINE`, `SMART_RENAME_TRIAGE_ENABLED`, `SMART_RENAME_PREFILTER`, `SMART_RENAME_REGROUP_AT`, `SMART_RENAME_MAX_CLAUSES`, `SMART_RENAME_L1_FAILS`, `SMART_RENAME_L2_FAILS`.

---

## 10. Testes (extensão)

Todos os 4 níveis da v1.5 se aplicam, com adições:

**Nível 1:**
- Triage: cada uma das 5 categorias retornadas corretamente, fallback em falha
- Generate: retry de regroup, guardrail de domínio, parsing do JSON rico
- Validate: todos os branches de render (session_kind + regrouped + anchor)

**Nível 2:**
- Fluxo Camada 1 → Camada 2 end-to-end com mocks
- Circuit breakers em cada camada

**Nível 3:**
- Sessão que naturalmente força reagrupamento (5+ cláusulas de mesmo tema)
- Sessão com pivot real (mudança de domain)
- Sessão de Q&A (deve ficar majoritariamente em `keep`)
- Sessão com falhas de LLM acionando circuit breaker

**Nível 4 (Computer Use):**
- Cenário de uso intensivo (>100 turnos) medindo custo real e taxa de decisões
- Rollback visual: forçar sessão que volta a foco anterior; verificar que título recupera

---

## 11. Riscos específicos da v2

| # | Risco | Mitigação |
|---|---|---|
| V1 | Camada 1 nunca economiza o suficiente para valer o custo adicional | Telemetria mede taxa de `keep` em uso real; se <50%, desativar triage |
| V2 | Haiku gera `session_kind` inconsistente entre turnos | Guardrail: só permite mudança de `session_kind` se confidence > 0.8 |
| V3 | Regroup retry falha e plugin fica em loop | Max 2 tentativas, fallback para título antigo |
| V4 | Guardrail domain↔pivot rejeita legítimos | Contador de `guardrail_rejected_consecutive`; após 3, loga alerta no explain |
| V5 | Stats agregadas crescem muito (centenas de sessões) | Cap e roll-over por mês em arquivo separado |

---

## 12. Rollout da v2

Diferente da v1.5 (que foi greenfield), a v2 é **aditiva**:

1. **Fase 1 — Opt-in silencioso:** módulos v2 instalados, `pipeline: "v15"` continua default. Usuário define `SMART_RENAME_PIPELINE=v2` para experimentar.
2. **Fase 2 — Coleta de dados:** logs registram comparações v1.5 vs v2 (se ambas rodassem, qual seria o título?).
3. **Fase 3 — Default v2:** depois de confirmado em uso real, `pipeline: "v2"` vira default.
4. **Fase 4 — Deprecação da v1.5:** se v2 se provar estrita superioridade, remover pipeline v15 em release futuro.

---

## 13. Definição de "pronto" para v2

- [ ] `scripts/lib/triage.sh` implementado com prompt + parsing + fallback
- [ ] `scripts/lib/generate.sh` absorvendo llm.sh da v1.5 e adicionando retry de regroup
- [ ] `scripts/lib/validate.sh` com branches de render
- [ ] `prompts/v2/*.md` (triage, generation, generation-regroup)
- [ ] Migração v1.5 → v2 testada
- [ ] Testes Nível 1-4 para módulos novos
- [ ] Subcomandos novos: stats, replay, classify
- [ ] Documentação atualizada mostrando pipeline como opt-in
- [ ] Pelo menos 5 sessões reais em modo v2 antes do default switch

---

## 14. Relação com a v1.5

Esta spec **não é independente**. Todo contexto arquitetural de baseline (componentes, work_score, throttling, structured output, skill, locking, logging, config) está em [v1.5 design](./2026-04-14-smart-session-rename-v15-design.md). A v2 se apoia nessa base e estende apenas o que acrescenta valor cognitivo.

O pré-requisito absoluto de construir a v2 é a validação de que a v1.5 foi adotada e está gerando valor mensurável. Sem essa validação, investir em Camada 1 + Camada 2 é prematuro e provavelmente desnecessário.

---

## Apêndice — Histórico desta spec

- **2026-04-07:** versão original, escrita como redesign completo da v1 (pré-investigação empírica do custo real do `claude -p`).
- **2026-04-14:** reenquadrada como "progressão a partir da v1.5" após brainstorming que cortou a ambição inicial diante dos dados empíricos de custo (~$0.10/chamada em OAuth) e da introdução do structured output nativo via `--json-schema`. Conteúdo cognitivo preservado; framing mudou de "substituir v1" para "evoluir v1.5".
