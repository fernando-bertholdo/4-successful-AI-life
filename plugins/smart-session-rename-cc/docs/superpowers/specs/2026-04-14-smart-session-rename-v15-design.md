# Smart Session Rename v1.5 — Design Spec

**Data:** 2026-04-14
**Autor:** Fernando + Claude (Opus 4.6 1M)
**Status:** Design aprovado em brainstorming, aguardando plano de implementação
**Versão:** 1.5
**Relação com versões:** substitui a v1 (greenfield — v1 nunca foi usada em prática). Define a base sobre a qual a v2 será construída.

---

## 1. Contexto e motivação

O plugin `claude-code-smart-session-rename` nasceu com a v1 (2026-03-24), que aplica uma lógica simples de renomeação: a cada três mensagens do usuário, chama Haiku com contexto raso e atualiza o título. A v1 foi implementada mas **nunca colocada em prática em uso real** — não há estado v1 legítimo no sistema do usuário, nem sessões em andamento que dependam do comportamento v1.

Em 2026-04-07 foi escrita uma proposta v2 ambiciosa (arquitetura de 2 camadas LLM, circuit breakers duplos, session_kind, regrouping, transition_history completo, 5 fases de rollout). Ao revisar essa proposta e fazer investigação empírica do `claude -p` em abril de 2026, três constatações mudaram o desenho:

1. **O custo real de `claude -p` em modo OAuth é ~$0.10/chamada** (não ~$0.0001 como o spec v2 presumia). O overhead vem de ~80k tokens de cache creation em cada invocação, porque o Claude Code carrega automaticamente todo o ambiente (tools, skills, MCPs, plugins, memória) em cada chamada.

2. **`claude -p` tem `--json-schema`** que produz output estruturado garantido pela Anthropic. Elimina a fragilidade de parsing JSON em bash que o spec v2 tentava mitigar via validação + retry.

3. **A arquitetura correta não é sofisticação cognitiva** (2 camadas LLM, circuit breakers por camada), **mas sofisticação determinística** (heurísticas de throttling que economizam dinheiro real). LLM vira uma ferramenta cara usada raramente.

A v1.5 é a resposta enxuta a essas três constatações. Ela entrega o valor central da visão v2 (formato `domain: clauses`, evolução semântica do título, controles manuais) com ~30% da complexidade, usando structured output nativo, uma única chamada LLM com throttling inteligente, e sem migração herdada.

## 2. Requisitos

### 2.1 Funcionais

- Sistema avalia a cada turno completo (Stop hook), mas **só chama LLM quando heurísticas determinísticas indicam que vale o custo**.
- Budget configurável por sessão (default 6 chamadas), com overflow de 2 slots manuais via `/smart-rename force`.
- Formato de título: `<domain>: <clause1>, <clause2>, ...` (ex: `auth: fix jwt expiry, add tests`).
- Quando chamada, LLM sempre retorna `{domain, clauses[]}`. Se o título renderizado é idêntico ao atual, plugin não re-escreve.
- Usuário pode: renomear manualmente, fixar domínio (anchor), congelar/descongelar atualizações, forçar uma reavaliação, e ver o status da sessão.
- `/rename` nativo do Claude Code é detectado e tratado como anchor implícito.

### 2.2 Não-funcionais

- **Modelo único:** Haiku 4.5.
- **Custo-alvo:** ~$0.60 por sessão típica de 50 turnos mistos (coding + Q&A), em modo OAuth sem API key separada. Baseline: ~$0.10/chamada × 6 chamadas.
- **Latência:** chamada LLM individual gasta 12-15s em OAuth (aceito, async não bloqueia sessão). Decisão determinística "não chamar" tem custo zero.
- **Não-bloqueante:** toda falha resulta em `exit 0` com log. Nunca propaga erro para a sessão do usuário.
- **Janela 64KB:** título é re-anexado ao JSONL a cada N turnos (configurável, default 10) para preservar visibilidade no seletor do Claude Code.

### 2.3 Fora do escopo da v1.5

Os itens abaixo estão **conscientemente deferidos para uma v2 futura** (ver `memory/project_v2_deferred.md`):

- Arquitetura de 2 camadas LLM (triage + generation)
- Classificação de `session_kind` (feature_work/bugfix/exploration/qa_session/review)
- Reagrupamento automático com retry de prompt
- Ação `rollback` via triage
- `transition_history` completo (v1.5 guarda apenas as 3 últimas transições significativas)
- Circuit breakers duplos por camada
- Análises estatísticas cross-sessão
- Migração de código para Node.js
- Suporte a múltiplos modelos
- Garbage collection de `custom-title` antigos no JSONL

### 2.4 Convenção de "turno"

- **Turno** = sequência contígua de eventos no JSONL que começa com uma mensagem do usuário (`type: "user"`) e termina no próximo `Stop` hook. Dentro de um turno pode haver múltiplos blocos do assistente (text + tool_use + text), característicos de loops agênticos do Claude Code moderno.
- **Mensagem do usuário do turno** = primeira (e única) entrada `type: "user"` do turno.
- **Blocos do assistente do turno** = todas as entradas `type: "assistant"` entre a mensagem do usuário e o fim do turno. Concatenar `text` blocks para análise textual.
- **Tool calls do turno** = todos os blocos `tool_use` dentro dos blocos do assistente do turno.
- **Arquivos tocados no turno** = paths extraídos dos tool calls (Read/Edit/Write/Bash com operações em files).

O módulo `lib/transcript.sh` (Seção 3.3) é o único responsável por implementar essa convenção.

---

## 3. Arquitetura

### 3.1 Diagrama do fluxo por turno

```
Stop hook do Claude Code dispara (async, timeout 30s)
        │
        ▼
┌────────────────────────────────────┐
│ 1. Carregar config + estado        │  ← lib/config.sh + lib/state.sh
│    Adquire lock (mkdir, stale-check)│
└────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────┐
│ 2. Detectar /rename nativo         │  ← compara último custom-title no JSONL
│    (seta manual_title_override)     │     com last_plugin_written_title
└────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────┐
│ 3. Parsear turno atual do JSONL    │  ← lib/transcript.sh
│    (user msg, assistant blocks,    │     extrai sinais para o scorer
│     tool calls, arquivos tocados)  │
└────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────┐
│ 4. Atualizar work_score            │  ← lib/scorer.sh
│    delta = tool_calls*1 +          │
│          new_files*3 + words*0.01  │
└────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────┐
│ 5. Decidir: chamar LLM?            │  ← lib/scorer.sh
│    (sequência de guards, Seção 4)  │
└────────────────────────────────────┘
        │
   ┌────┴────┐
 não         sim
   │           │
   ▼           ▼
┌────────┐  ┌────────────────────────────┐
│ Re-    │  │ 6. Chamar LLM (Haiku 4.5)  │  ← lib/llm.sh
│ anexar │  │    claude -p --json-schema │
│ título │  │    retorna {domain,clauses}│
│ a cada │  └────────────────────────────┘
│ N turn │           │
└────────┘           ▼
   │         ┌────────────────────────────┐
   │         │ 7. Validar + renderizar    │  ← lib/validate.sh
   │         │    se igual ao atual: skip │
   │         │    se diff: escreve JSONL  │
   │         └────────────────────────────┘
   │                 │
   ▼                 ▼
┌────────────────────────────────────┐
│ 8. Atualizar estado + log + unlock │  ← lib/state.sh + lib/logger.sh
└────────────────────────────────────┘
```

### 3.2 Princípios arquiteturais

- **Separação cognitiva vs determinística.** A LLM decide *como nomear quando chamada*. Todo o *quando chamar* é determinístico, controlável e testável.
- **Peso do determinismo.** Dado o custo alto de LLM em modo OAuth, o `scorer` é a peça mais importante arquiteturalmente. Ele economiza dinheiro real a cada decisão "não chamar".
- **Falhas isoladas.** Cada falha termina em log + exit 0. Nunca bloqueia o usuário. Um circuit breaker simples (não dois como no spec v2) desabilita LLM após 3 falhas consecutivas.
- **Structured output nativo.** Usa `--json-schema` do `claude -p`. A Anthropic garante que o output conforme o schema. Eliminando parsing frágil, o código v1.5 vira significativamente mais simples que a v1 ou o spec v2 seriam.
- **Idempotência por assinatura.** `last_processed_signature` no estado (formato `turn_number:file_size`) evita reprocessamento em caso de re-execução do hook no mesmo turno, **e cobre loops agênticos** onde o Stop hook pode disparar várias vezes no mesmo turno com o JSONL crescendo entre disparos.

### 3.3 Estrutura de diretórios

```
claude-code-smart-session-rename/
├── .claude-plugin/
│   └── plugin.json                      # manifesto (atualiza version → 1.5)
├── hooks/
│   └── hooks.json                       # Stop hook (inalterado em relação à v1)
├── config/
│   └── default-config.json              # defaults v1.5
├── scripts/
│   ├── rename-hook.sh                   # entry point, ~80 linhas
│   ├── smart-rename-cli.sh              # entry point dos subcomandos da skill
│   ├── lib/
│   │   ├── config.sh                    # load de config + env vars
│   │   ├── state.sh                     # load/save/lock do estado JSON
│   │   ├── transcript.sh                # parsing do JSONL da sessão
│   │   ├── scorer.sh                    # work_score + decisão de chamada
│   │   ├── llm.sh                       # wrapper de claude -p
│   │   ├── writer.sh                    # append de custom-title
│   │   ├── validate.sh                  # validação + render do título
│   │   └── logger.sh                    # logs JSONL estruturados
│   └── prompts/
│       └── generation.md                # prompt da LLM (iterável sem mexer em código)
├── skills/
│   └── smart-rename/
│       └── SKILL.md                     # orienta o Claude a invocar smart-rename-cli.sh
└── tests/
    ├── run-tests.sh
    ├── fixtures/                        # JSONLs para parser + cenários de scorer
    ├── unit/                            # um arquivo por módulo em lib/
    └── integration/                     # fluxo end-to-end com LLM mockada
```

### 3.4 Componentes e responsabilidades

| Módulo | Responsabilidade | Interface |
|---|---|---|
| `rename-hook.sh` | Entry point do Stop hook; orquestra os 8 passos | stdin: `{session_id, transcript_path, cwd}` |
| `smart-rename-cli.sh` | Entry point dos subcomandos da skill | `$1` = subcomando; args variam |
| `lib/config.sh` | Carrega config com precedência env > file > defaults | `config_load()`, `config_get(key)` |
| `lib/state.sh` | Load/save atômico, locking, stale check | `state_load()`, `state_save()`, `state_lock()`, `state_unlock()` |
| `lib/transcript.sh` | Parse do JSONL do turno atual | `transcript_parse_current_turn(path) → JSON` (schema na Seção 3.5) |
| `lib/scorer.sh` | Fórmula do delta e decisão binária | `scorer_compute_delta(turn_data)`, `scorer_should_call_llm(state, new_score)` |
| `lib/llm.sh` | Wrapper de `claude -p` com timeout | `llm_generate_title(context_json) → JSON ou erro` |
| `lib/writer.sh` | Append de `custom-title` no JSONL | `writer_append_title(transcript_path, title)` |
| `lib/validate.sh` | Valida schema, aplica guardrails, renderiza | `validate_and_render(llm_output, state) → title ou SKIP` |
| `lib/logger.sh` | Logs JSONL estruturados | `log_event(level, event_type, data_json)` |
| `prompts/generation.md` | Prompt da LLM com variáveis | substituídas via `jq --rawfile + gsub` no `llm.sh` (seguro para multi-linha, aspas, barras) |

### 3.5 Schema do output do `transcript_parse_current_turn`

O parser emite um JSON em stdout consumido por `scorer.sh`, `llm.sh` e `validate.sh`:

```json
{
  "turn_number": 14,
  "user_msg": "Add rate limiting to the auth endpoints",
  "user_word_count": 7,
  "assistant_text": "I'll add rate limiting using express-rate-limit...",
  "assistant_sentence_count": 3,
  "tool_call_count": 4,
  "tool_names": ["Read", "Edit", "Edit", "Bash"],
  "all_files_touched": ["src/auth/rate-limit.ts", "tests/auth.test.ts"],
  "new_files_this_turn": ["src/auth/rate-limit.ts"],
  "domain_guess": "auth",
  "branch": "feat/auth-hardening",
  "file_size": 8432
}
```

`new_files_this_turn` é computado comparando contra `state.active_files_recent`. `domain_guess` é uma heurística leve: diretório dominante (token mais frequente) entre `all_files_touched`, ou fallback para o último segmento do `cwd` (passado explicitamente pelo hook via argumento, **não** lido de `$PWD`). `file_size` é `wc -c` do transcript inteiro e alimenta a `last_processed_signature` do hook (Seção 6.4) — essencial para cobrir Stop hooks múltiplos no mesmo turno agêntico.

O parser aceita `content` tanto como string quanto como array (caso comum em mensagens de usuário com `tool_result` + `text` blocks) — no segundo caso, concatena os text blocks.

---

## 4. Lógica do throttling (coração da v1.5)

### 4.1 Fórmula do work_score

Por turno, calcula-se o delta:

```
delta = tool_calls_in_turn
      + new_files_in_turn * 3
      + user_words_in_turn * 0.01
```

Justificativa dos pesos:
- **tool_calls, peso 1:** sinal de atividade, cada um contribui modestamente
- **new_files, peso 3:** forte indicador de mudança de escopo; tocar arquivo novo sugere trabalho semanticamente diferente
- **user_words, peso 0.01:** palavras contribuem marginalmente; evita que mensagens longas (sem ação) dominem o score

O estado acumula:
```
accumulated_score += delta   # a cada turno
```
Resetado para 0 após cada chamada LLM bem-sucedida.

### 4.2 Sequência de guards de decisão

Ordem importa — primeiro match decide:

```
1. Se state.frozen == true:
      decisão = SKIP
      (caminho de "frozen": só re-anexa título a cada reattach_interval turnos)

2. Se state.force_next == true:
      decisão = CALL
      state.force_next = false    # consome flag
      (se budget esgotado mas overflow disponível: consome overflow)

3. Se state.llm_disabled == true (circuit breaker ativo):
      decisão = SKIP

4. Se state.calls_made >= max_budget_calls + state.overflow_used:
      decisão = SKIP (budget esgotado; log "budget_exhausted")

5. Se state.title_struct == null (primeira chamada):
      se accumulated_score >= first_call_work_threshold (20):
            decisão = CALL
      senão: SKIP

6. Senão (chamadas subsequentes):
      se accumulated_score >= ongoing_work_threshold (40):
            decisão = CALL
      senão: SKIP
```

### 4.3 Exemplo numérico

Sessão de 50 turnos mistos:

| Turno | Eventos | delta | acc | Decisão |
|---|---|---|---|---|
| 1 | user msg curta, 0 tool calls | 0.5 | 0.5 | SKIP (abaixo de 20) |
| 2 | 3 Read, 2 new files | 9 | 9.5 | SKIP |
| 3 | 2 Edit, 1 Bash, msg 150 palavras | 4.5 | 14 | SKIP |
| 4 | 2 Read, 1 Write, 1 new file | 6 | 20 | **CALL** (primeira, ≥20) · reset acc=0 |
| 5-10 | trabalho normal (~6/turno) | 6 | 36 | SKIP |
| 11 | 3 Edit, 1 new file | 6 | 42 | **CALL** (≥40) · reset acc=0 |
| 12-22 | trabalho e Q&A | ~4/turno | 44 | **CALL** · reset |
| ... | ... | ... | ... | ... |
| 50 | fim da sessão | | | total: ~5-6 CALLs |

Custo esperado: ~6 × $0.10 = **$0.60/sessão**.

### 4.4 Re-anexação periódica do título

Mesmo em turnos com decisão SKIP, o título atual é re-anexado ao JSONL a cada `reattach_interval` turnos (default 10). Isso preserva o título dentro da janela 64KB que o Claude Code escaneia, garantindo que ele apareça no seletor de sessões.

---

## 5. Interação com a LLM

### 5.1 Chamada `claude -p`

```bash
claude -p \
  --model "${SMART_RENAME_MODEL:-claude-haiku-4-5}" \
  --output-format json \
  --no-session-persistence \
  --json-schema "${JSON_SCHEMA}" \
  "${RENDERED_PROMPT}" \
  2>/dev/null
```

Timeout no shell: wrapper portável. `llm.sh` tenta `timeout`, depois `gtimeout` (GNU coreutils via brew), depois `perl -e 'alarm shift; exec @ARGV'` como fallback. **Nunca assumir que `timeout` existe** — ele não está disponível por default no macOS (que é a plataforma alvo do Level 4 via Computer Use). O wrapper é transparente para o caller (sempre chama `_llm_with_timeout "$seconds" claude -p ...`).

### 5.2 JSON schema

```json
{
  "type": "object",
  "properties": {
    "domain": {
      "type": "string",
      "minLength": 1,
      "maxLength": 30,
      "description": "Short slug describing the session's subject area (≤3 words)"
    },
    "clauses": {
      "type": "array",
      "items": {"type": "string", "minLength": 2, "maxLength": 50},
      "minItems": 1,
      "maxItems": 5,
      "description": "Ordered list of '[verb] [entity]' phrases describing work done"
    }
  },
  "required": ["domain", "clauses"],
  "additionalProperties": false
}
```

### 5.3 Extração do output

```bash
structured=$(echo "$raw_output" | jq -r '.[-1].structured_output // empty')
```

O campo `.structured_output` é preenchido pelo Claude Code quando `--json-schema` é usado; contém JSON válido garantido pela Anthropic.

### 5.4 Prompt (`prompts/generation.md`)

Template com variáveis `${VAR}` substituídas via `jq -nr --rawfile tmpl --argjson ctx '...' | reduce ... (gsub(...))` — abordagem segura para valores com newlines, aspas, barras e caracteres especiais. **Nunca usar `sed` ou `envsubst`** (quebra em valores multi-linha):

```markdown
You are generating a concise title for an ongoing Claude Code session.

CURRENT TITLE: ${CURRENT_TITLE:-<not yet named>}
MANUAL ANCHOR: ${MANUAL_ANCHOR:-<none>}
CURRENT BRANCH: ${BRANCH}
DOMAIN GUESS: ${DOMAIN_GUESS}
RECENT FILES: ${RECENT_FILES}

USER MESSAGE (this turn):
${USER_MSG}

ASSISTANT SUMMARY (this turn, truncated):
${ASSISTANT_SUMMARY}

RECENT CONTEXT (last 3 turns):
${RECENT_TURNS}

RULES:
- Produce `{domain, clauses[]}` in the schema provided.
- `domain`: short slug (1-3 words) naming the subject area (e.g., "auth", "deploy-pipeline").
- If MANUAL ANCHOR is set, use it exactly as `domain`.
- `clauses`: 1 to 5 items, each `[verb] [concrete entity]` (e.g., "fix jwt expiry", "add tests").
  - Avoid generic jargon ("implementation", "enhancement").
  - Prefer active verbs; entities should be concrete (file, module, behavior).
- If nothing substantial changed versus CURRENT TITLE, return the same structure anyway (plugin will deduplicate).
```

### 5.5 Validação e render

Após obter `{domain, clauses[]}`:

1. **Precedência de override:** se `state.manual_title_override != null`, retorna o override como `rendered_title` verbatim (sem `clauses`, sem prefixo de domain) e pula as regras 2-4.
2. **Schema garantido pelo claude -p**; ainda assim, validação defensiva: `domain` não vazio, `clauses` array não vazio, items com comprimento razoável.
3. **Guardrail de anchor:** se `state.manual_anchor != null`, sobrescreve `domain` com o valor do anchor.
4. **Dedupe de cláusulas:** lowercase + trim + colapso de whitespace; cláusulas normalizadas idênticas são mescladas (mantém primeira ocorrência).
5. **Render:** `title = "${domain}: ${clauses.join(', ')}"`.
6. **Comparação:** se `rendered_title == state.rendered_title`, retorna SKIP (não chama writer).

---

## 6. Estado da sessão

### 6.1 Schema (`${CLAUDE_PLUGIN_DATA}/state/{session_id}.json`)

```json
{
  "version": "1.5",
  "rendered_title": "auth: fix jwt expiry, add tests",
  "last_plugin_written_title": "auth: fix jwt expiry, add tests",
  "title_struct": {
    "domain": "auth",
    "clauses": ["fix jwt expiry", "add tests"]
  },
  "manual_anchor": null,
  "manual_title_override": null,
  "frozen": false,
  "force_next": false,

  "accumulated_score": 12.5,
  "calls_made": 2,
  "overflow_used": 0,
  "failure_count": 0,
  "llm_disabled": false,
  "last_processed_signature": "14:8432",

  "domain_guess": "auth",
  "active_files_recent": ["src/auth/jwt.ts", "src/auth/rate-limit.ts"],
  "branch": "feat/auth-hardening",

  "transition_history": [
    {"turn": 4, "title": "auth: fix jwt expiry", "reason": "first"},
    {"turn": 11, "title": "auth: fix jwt expiry, add tests", "reason": "extend"}
  ],

  "created_at": "2026-04-14T10:30:00Z",
  "updated_at": "2026-04-14T11:20:00Z"
}
```

`transition_history` guarda apenas transições com mudança de título (CALL com output diferente), até 3 itens mais recentes. Keeps e SKIPs não são registrados aqui — o log JSONL (Seção 9) captura tudo.

### 6.2 Locking e atomicidade

- **Lock:** `mkdir ${statefile}.lockdir` (atômico em todos os POSIX).
- **Stale check:** se `mtime do lockdir > lock_stale_seconds (default 60s, deliberadamente ≥ 2× `llm_timeout_seconds` para evitar race entre hook longo e hook órfão)`, remove como órfão.
- **Retry:** até 2s com passos de 0.5s. Falha de aquisição = skip silencioso (preserva "nunca bloqueia").
- **Escrita atômica:** `temp_file + mv -f`.

---

## 7. Skill `/smart-rename`

### 7.1 Mecanismo

A skill é uma instrução em `skills/smart-rename/SKILL.md` lida pelo Claude Code dentro da sessão quando o usuário invoca `/smart-rename [args]`. A skill orienta o Claude a executar `scripts/smart-rename-cli.sh <subcomando>` via Bash tool. O CLI é quem de fato manipula o estado e o JSONL.

**Validação empírica requerida na Fase 1 da implementação:** antes de investir nos 7 subcomandos, construir protótipo mínimo com apenas `freeze` para confirmar que o Claude dentro da sessão consegue: (a) executar scripts do plugin via Bash, (b) identificar o `session_id` corretamente (via env var ou derivando do `transcript_path`), (c) sem race condition perigoso com o Stop hook do próprio turno da skill.

### 7.2 Subcomandos

| Comando | Efeito no estado | Chama LLM? |
|---|---|---|
| `/smart-rename` | Lê estado + transcript, chama LLM bypassando scorer, mostra sugestão, espera aprovação, se aprovado chama writer | Sim (+1 budget) |
| `/smart-rename <nome>` | Writer escreve `<nome>` primeiro; se OK, seta `manual_anchor = <nome>`, limpa `manual_title_override` | Não |
| `/smart-rename freeze` | `frozen = true` | Não |
| `/smart-rename unfreeze` | `frozen = false` | Não |
| `/smart-rename force` | `force_next = true` (consumido pelo próximo Stop hook) | Não diretamente |
| `/smart-rename explain` | Lê estado + últimos eventos do log; formata saída human-readable | Não |
| `/smart-rename unanchor` | Limpa **ambos** `manual_anchor = null` e `manual_title_override = null` (retorno único ao modo automático) | Não |

### 7.3 Saída de `/smart-rename explain`

```
Título atual: auth: fix jwt expiry, add tests
Domínio: auth (anchor: —)
Estado: ativo (não congelado)

Budget: 2/6 chamadas usadas, 4 restantes · overflow 0/2
Circuit breaker: OK (0 falhas consecutivas)
Work score acumulado: 12.5 (próximo call em ≥40)

Últimas transições:
  turno 4  → auth: fix jwt expiry                   (first)
  turno 11 → auth: fix jwt expiry, add tests        (extend)

Último evento do log:
  2026-04-14T11:20:01Z turn=14 event=score_update delta=6 acc=12.5
```

### 7.4 Detecção de `/rename` nativo

O `/rename` nativo do Claude Code escreve um `custom-title` diretamente no JSONL com **texto livre** (não necessariamente um slug). Tratá-lo como `manual_anchor` (domain slug para o render `domain: clauses`) produz títulos esteticamente quebrados como `"Meu titulo livre: add tests, fix bug"`. Por isso separamos:

- **`manual_anchor`**: domínio em formato slug, setado por `/smart-rename <slug>` — entra no render normal `anchor: clauses`.
- **`manual_title_override`**: título bruto, setado pela detecção de `/rename` nativo — renderizado **verbatim**, sem cláusulas.

A cada execução do hook, antes de qualquer decisão:

1. Lê o **último** `custom-title` do JSONL (em ordem de aparição no arquivo).
2. Compara com `state.last_plugin_written_title`.
3. Se diferem: ocorreu rename manual nativo. Plugin seta:
   - `state.manual_title_override = <último custom-title>`
   - `state.rendered_title = <último custom-title>`
   - `state.last_plugin_written_title = <último custom-title>` (evita detecção duplicada)
   - Registra entrada `{turn: N, title: ..., reason: "manual_rename"}` em `transition_history`.
4. Se iguais: nenhum rename manual, segue fluxo normal.

O renderer da Seção 5.5 dá precedência a `manual_title_override` (verbatim) > `manual_anchor` (domain) > domain gerado pela LLM.

Para limpar **ambos** os estados manuais de uma vez (voltar ao modo totalmente automático): `/smart-rename unanchor`. Esse comando limpa tanto `manual_anchor` quanto `manual_title_override` para simplificar a UX — não há caminho de limpeza separada.

---

## 8. Tratamento de erros e circuit breaker

### 8.1 Princípio fundamental

**Toda falha interna termina em `exit 0`.** Hook nunca quebra a sessão. Toda lógica converge para: log estruturado + degrade gracioso + sair limpo.

### 8.2 Matriz de falhas

| Falha | Detecção | Tratamento |
|---|---|---|
| `claude -p` erro/timeout | `result.is_error == true` ou exit ≠ 0 | `failure_count++`, log warn, mantém título |
| Output inválido (schema não honrado) | jq retorna null ou validate falha | `failure_count++`, log warn, mantém título |
| Transcript ausente/ilegível | `[ ! -r "$path" ]` | Log warn "transcript missing", sai |
| Estado JSON corrompido | jq não parseia | Log error, renomeia para `*.corrupt.bak`, recria estado vazio |
| Lock não adquirido em 2s | timeout no retry loop | Log info "lock contention", sai |
| Lock órfão | mtime > lock_stale_seconds (60s) | Remove, adquire, log info |
| `CLAUDE_PLUGIN_DATA` não setado | env check no início | Log error, sai |
| `claude` CLI ausente | `command -v claude` | Log error, marca `llm_disabled`, sai |
| `jq` ausente | `command -v jq` | Log error fatal, sai |

### 8.3 Circuit breaker simples

```
on failure: failure_count++
if failure_count >= 3:
    llm_disabled = true
    log warn "circuit breaker tripped"
on success: failure_count = 0
on /smart-rename force: failure_count = 0, llm_disabled = false (reset manual)
```

Quando `llm_disabled == true`, `scorer_should_call_llm()` retorna sempre SKIP. Plugin continua re-anexando título atual periodicamente.

### 8.4 Idempotência

`last_processed_signature` (formato `turn_number:file_size`) evita reprocessamento em race **e cobre loops agênticos** onde o Stop hook pode disparar várias vezes no mesmo turno com JSONL crescendo entre disparos:

```
signature = turn_number + ":" + file_size (em bytes)
if signature == state.last_processed_signature:
    # hook rodando duas vezes para o mesmo snapshot do transcript
    apenas re-anexa título se aplicável
    não atualiza work_score
    não chama LLM
    sai
# Se turn_number é o mesmo mas file_size cresceu (novo bloco de assistant
# apareceu durante um loop agêntico), a signature mudou e o hook processa
# o novo conteúdo.
```

**Importante:** a signature é avançada apenas em saídas consistentes — skip, skip_identical, ok+writer_success, invalid, LLM error. **Não** é avançada em ok+writer_failure, para permitir retry do writer no próximo hook.

---

## 9. Logs e observabilidade

### 9.1 Formato

Arquivo: `${CLAUDE_PLUGIN_DATA}/logs/{session_id}.jsonl` — uma linha por evento.

```jsonl
{"ts":"2026-04-14T11:20:01Z","turn":14,"event":"score_update","delta":6,"acc":18.5}
{"ts":"2026-04-14T11:20:01Z","turn":14,"event":"llm_decision","decision":"skip","reason":"below_threshold","acc":18.5,"threshold":40}
{"ts":"2026-04-14T11:20:15Z","turn":15,"event":"llm_call_start","model":"claude-haiku-4-5","calls_made":2,"budget_remaining":4}
{"ts":"2026-04-14T11:20:22Z","turn":15,"event":"llm_call_end","duration_ms":6800,"cost_usd":0.098,"output":{"domain":"auth","clauses":["fix jwt expiry","add tests"]}}
{"ts":"2026-04-14T11:20:22Z","turn":15,"event":"title_written","title":"auth: fix jwt expiry, add tests"}
{"ts":"2026-04-14T11:20:22Z","turn":15,"event":"state_saved"}
```

### 9.2 Eventos

`score_update`, `llm_decision`, `llm_call_start`, `llm_call_end`, `llm_error`, `title_written`, `title_skipped`, `title_reattached`, `manual_rename_detected`, `manual_anchor_set`, `freeze_toggled`, `force_triggered`, `budget_exhausted`, `overflow_used`, `circuit_breaker_tripped`, `circuit_breaker_reset`, `lock_stale_cleaned`, `state_corrupted_recovered`, `state_saved`.

### 9.3 Níveis

`SMART_RENAME_LOG_LEVEL`: `debug | info | warn | error`. Default `info`.

---

## 10. Configuração

### 10.1 `config/default-config.json`

```json
{
  "enabled": true,
  "model": "claude-haiku-4-5",

  "max_budget_calls": 6,
  "overflow_manual_slots": 2,
  "first_call_work_threshold": 20,
  "ongoing_work_threshold": 40,

  "reattach_interval": 10,
  "circuit_breaker_threshold": 3,
  "lock_stale_seconds": 60,
  "llm_timeout_seconds": 25,

  "log_level": "info",
  "max_clauses": 5,
  "max_domain_chars": 30,
  "max_user_msg_chars": 500,
  "max_assistant_chars": 500
}
```

### 10.2 Variáveis de ambiente

Precedência: env > `${CLAUDE_PLUGIN_DATA}/config.json` > `config/default-config.json`.

| Campo | Variável |
|---|---|
| `enabled` | `SMART_RENAME_ENABLED` |
| `model` | `SMART_RENAME_MODEL` |
| `max_budget_calls` | `SMART_RENAME_BUDGET_CALLS` |
| `overflow_manual_slots` | `SMART_RENAME_OVERFLOW_SLOTS` |
| `first_call_work_threshold` | `SMART_RENAME_FIRST_THRESHOLD` |
| `ongoing_work_threshold` | `SMART_RENAME_ONGOING_THRESHOLD` |
| `reattach_interval` | `SMART_RENAME_REATTACH_INTERVAL` |
| `circuit_breaker_threshold` | `SMART_RENAME_CB_THRESHOLD` |
| `llm_timeout_seconds` | `SMART_RENAME_LLM_TIMEOUT` |
| `log_level` | `SMART_RENAME_LOG_LEVEL` |

---

## 11. Estratégia de testes

Esta v1.5 adota **cobertura máxima de todos os níveis possíveis**, incluindo validação empírica end-to-end via Computer Use do Claude Code CLI.

### 11.1 Nível 1 — Testes unitários

Um arquivo de teste por módulo em `tests/unit/`, usando bash + assert helpers (compatível com o estilo atual do projeto).

Cobertura mínima:

- **`config.sh`:** precedência env > file > defaults; cada campo individualmente; valores inválidos.
- **`state.sh`:** load com arquivo ausente; save atômico; lock aquisição OK; lock stale removido; concorrência simulada.
- **`transcript.sh`:** parse de turno simples; turno com loop agêntico (múltiplos blocks + tool_use); extração de arquivos; turno sem tool calls.
- **`scorer.sh`:** fórmula do delta em cenários variados; matriz completa de guards; idempotência via `last_processed_signature`.
- **`validate.sh`:** render em todos os branches (padrão, com anchor, dedupe de clauses, comparação SKIP).
- **`writer.sh`:** append correto; erro de permissão; verificação de integridade.
- **`logger.sh`:** formato JSONL válido; filtro por nível; rotação se aplicável.

### 11.2 Nível 2 — Testes de integração com LLM mockada

Em `tests/integration/`:

- Fixtures completas de JSONL em `tests/fixtures/` simulando sessões reais (bugfix curto, feature longa, Q&A exploratório, sessão com rename manual nativo no meio).
- Mock de `claude -p` via wrapper em `$PATH` de teste que retorna respostas canônicas ou simula falhas.
- Verifica: decisão CALL vs SKIP em cada fixture; escrita correta do `custom-title`; estado salvo corretamente; circuit breaker dispara após 3 falhas consecutivas; re-anexação periódica funciona; detecção de `/rename` nativo.

### 11.3 Nível 3 — Testes de sanidade com LLM real (manual, opcional)

Em `tests/scenarios/`:

- Roteiros detalhados que o desenvolvedor executa manualmente em uma sessão real.
- Objetivo: auditar custo real vs estimado, calibrar `first_call_work_threshold` e `ongoing_work_threshold` baseado em dados, verificar qualidade dos títulos gerados.
- Não roda em CI (custo e variabilidade). Resultado fica documentado em `docs/test-results/YYYY-MM-DD.md`.

### 11.4 Nível 4 — Testes de usabilidade via Computer Use (executados pelo agente)

**Nova capacidade** habilitada pelo Computer Use do Claude Code CLI (v2.1.85+, Pro/Max, macOS).

O agente (Claude nesta sessão de desenvolvimento) executa validação end-to-end real:

**Setup:**
- Habilitar `computer-use` MCP via `/mcp` menu na sessão interativa.
- Conceder permissões de Accessibility e Screen Recording no macOS.
- Ter o plugin v1.5 instalado no diretório de desenvolvimento local.

**Cenários que o agente executa via Computer Use:**

1. **Smoke test da instalação:**
   - Abre novo terminal → inicia `claude` em modo interativo em um projeto de teste
   - Envia mensagem "Add a function to sum two numbers in src/math.js"
   - Aguarda turno completar
   - Verifica (via leitura do JSONL e via abrir `/resume` e ver título no seletor) que o primeiro `custom-title` apareceu após atingir work_score threshold
   - Screenshot do seletor de sessões

2. **Evolução incremental de título:**
   - Continuação da sessão anterior com novos pedidos ao longo de ~20 turnos
   - Monitora estado em `${CLAUDE_PLUGIN_DATA}/state/{id}.json` entre turnos
   - Verifica que `calls_made` progride conforme heurísticas, não a cada turno
   - Verifica que `transition_history` captura as transições significativas

3. **Teste de controles manuais:**
   - Invoca `/smart-rename freeze`, envia mais turnos, verifica que título não muda
   - Invoca `/smart-rename unfreeze`, verifica retomada
   - Invoca `/smart-rename force`, verifica chamada LLM imediata
   - Invoca `/smart-rename <nome>`, verifica anchor aplicado
   - Invoca `/smart-rename explain`, screenshot da saída

4. **Teste de rename nativo:**
   - Usa `/rename` nativo do Claude Code para renomear manualmente
   - Continua a sessão e verifica que o plugin passa a respeitar o domínio manual (anchor implícito)

5. **Teste de falha do LLM:**
   - Configura mock/rate-limit artificial para forçar 3 falhas consecutivas
   - Verifica circuit breaker tripping e saída do `/smart-rename explain`

**Relatórios:** cada execução produz um markdown em `docs/test-results/usability-YYYY-MM-DD.md` com screenshots, observações, bugs encontrados e ajustes sugeridos.

**Limitações:**
- Computer Use só em sessão interativa (não em `-p`). Então o agente executa as validações em um terminal separado controlado via Computer Use.
- Um lock global por máquina; não paraleliza com outras sessões usando Computer Use.
- macOS only nesta versão.

### 11.5 CI

- Níveis 1 e 2 em cada push (custo zero, determinísticos).
- Shellcheck como gate.
- Nível 3 e 4 rodados manualmente (agente ou desenvolvedor).

---

## 12. Riscos e mitigações

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|
| 1 | Custo real em uso intensivo (~$0.60/sessão × N sessões/dia) | Alta | Médio | Budget hard, logs expõem custo total, `SMART_RENAME_ENABLED=false` como escape hatch |
| 2 | Work_score mal calibrado (chama demais ou de menos) | Alta | Baixo | Env vars para calibração fácil; Nível 4 testa em uso real |
| 3 | `claude -p` muda interface (flags, formato) | Baixa | Alto | Wrapper em `lib/llm.sh`; teste de integração valida contrato |
| 4 | Haiku gera clauses genéricas ou sem sentido | Média | Médio | Prompt com regras explícitas + dedupe; se qualidade ruim, iterar `prompts/generation.md` |
| 5 | Claude Code muda formato JSONL da sessão | Baixa | Alto | Parser isolado em `lib/transcript.sh`; uso de `jq // empty` defensivo |
| 6 | `/rename` nativo escrito no JSONL antes do hook ler | Baixa | Baixo | Comparação via `last_plugin_written_title` resolve |
| 7 | Skill dentro da sessão não consegue executar scripts | Média | Alto | Fase 1 da implementação valida protótipo antes de investir nos 7 subcomandos |
| 8 | Lock órfão de processo morto | Média | Médio | Stale check (>60s; 2× llm_timeout) |
| 9 | Estado JSON corrompido | Baixa | Médio | Recovery para `*.corrupt.bak` + estado vazio |
| 10 | `transition_history` cresce (mitigado para 3) | Baixa | Baixo | Hard cap em 3 itens na escrita |
| 11 | JSONL acumula `custom-title` records em sessões gigantes | Alta (longo prazo) | Baixo | Limitação conhecida; aceita; GC fica para v2 |

---

## 13. Plano de rollout

Como a v1 nunca foi usada em prática, não há fases gradativas de rollout. A sequência é:

1. **Fase 1 — Protótipo mínimo da skill (validação de mecanismo):** construir apenas `scripts/smart-rename-cli.sh freeze` + SKILL.md mínimo. Testar via Computer Use que o Claude dentro da sessão consegue executar e modificar estado. Se falhar, ajustar mecanismo antes de investir.
2. **Fase 2 — Implementação modular por camadas:** `lib/config.sh` + `lib/state.sh` + `lib/logger.sh` primeiro (base), depois `lib/transcript.sh` + `lib/scorer.sh` (coração), depois `lib/llm.sh` + `lib/validate.sh` + `lib/writer.sh` (integração), por fim `rename-hook.sh` (orquestração) e demais subcomandos da skill.
3. **Fase 3 — Testes Nível 1 e 2 passando em CI.**
4. **Fase 4 — Sanidade manual (Nível 3) em 2-3 sessões reais.** Calibrar thresholds se necessário.
5. **Fase 5 — Usabilidade via Computer Use (Nível 4)** executada pelo agente. Relatórios em `docs/test-results/`.
6. **Fase 6 — Documentação do usuário atualizada** (`README.md`, `CHANGELOG.md`).
7. **Fase 7 — Release.** Tag `v1.5.0`.

---

## 14. Definição de "pronto"

- [ ] Todos os módulos de `scripts/lib/` implementados conforme Seção 3.4
- [ ] `rename-hook.sh` orquestrando os 8 passos
- [ ] `scripts/prompts/generation.md` com prompt iterável
- [ ] `smart-rename-cli.sh` + `SKILL.md` implementando os 7 subcomandos
- [ ] Locking + stale check + escrita atômica
- [ ] Idempotência via `last_processed_signature` (cobrindo multi-Stop agêntico)
- [ ] Detecção de `/rename` nativo via `last_plugin_written_title`
- [ ] Logs JSONL estruturados (Seção 9)
- [ ] Configuração com precedência env > file > defaults (Seção 10)
- [ ] Testes Nível 1 cobrindo todos os módulos
- [ ] Testes Nível 2 cobrindo 4 fixtures de sessões
- [ ] Pelo menos 2 cenários do Nível 3 documentados
- [ ] Pelo menos 3 cenários do Nível 4 (Computer Use) executados e relatados
- [ ] README + CHANGELOG atualizados
- [ ] Shellcheck passando em todos os scripts

---

## 15. Relação com a v2

A v2 (ver `docs/superpowers/specs/2026-04-07-smart-session-rename-v2-design.md`, a ser adaptado para indicar progressão a partir desta v1.5) é o próximo passo **contingente**: só vale construir se a v1.5 for usada regularmente e o valor percebido justificar investir em sofisticação cognitiva adicional.

Os itens explicitamente deferidos para v2 estão registrados em `memory/project_v2_deferred.md` e não devem ser esquecidos entre sessões.
