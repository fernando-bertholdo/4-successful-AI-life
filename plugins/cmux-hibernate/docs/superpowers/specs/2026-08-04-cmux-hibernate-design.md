# cmux-hibernate — Design

**Data:** 2026-08-04
**Status:** Aprovado (aguarda plano de implementação)
**Autor:** Fernando Bertholdo

---

## 1. Problema

O cmux mantém dezenas de abas de terminal, muitas rodando sessões do Claude Code. Com
o computador ligado por longos períodos, a máquina chega perto do limite de memória e
CPU. A vontade é dar `Cmd+Q` no cmux — para reiniciar o computador ou apenas liberar
recursos para outra tarefa pesada — mas hoje isso é arriscado:

1. **O `resumeBinding` do cmux envelhece.** Ele registra a *intenção* gravada por um
   hook, não o estado do processo. Quando uma sessão é retomada e passa a gravar sob
   outro ID, o binding continua apontando para o ID antigo. Num ciclo real de
   fechar/reabrir, isso escondeu 7 conversas — uma delas com 5,2 MB de histórico.
2. **Reabrir sobe tudo de uma vez.** Abas com `auto_resume: true` executam na abertura,
   recriando exatamente o consumo de memória que motivou o fechamento.
3. **Abas fechadas perdem a referência.** Sem registro externo, uma aba encerrada leva
   junto o vínculo sessão ↔ workspace, mesmo com o transcript intacto em disco.

## 2. Objetivo

Permitir fechar o cmux por vontade própria, a qualquer momento, com garantia de que o
ambiente volta ao lugar — e voltando **leve**, sem recriar o peso que motivou o
fechamento.

### Não-objetivos

- Não substitui o mecanismo de restauração do cmux. Ele acerta a estrutura; o plugin
  corrige os vínculos.
- Não mantém registro contínuo nem hooks em segundo plano (ver §3.1).
- Não é ferramenta de recuperação de desastre. O gatilho é sempre deliberado.
- Não tenta ser portável para outros multiplexadores. É específico do cmux.

## 3. Decisões de design

### 3.1 Sem hook, sem registro contínuo

**Decisão:** o estado é derivado sob demanda, no momento do `hibernate`, com o cmux vivo.

**Porquê:** um registro que afirma "estas sessões existem" apodrece — acumula conversas
encerradas que ninguém concilia, e o custo de mantê-lo verdadeiro cresce sem limite. Como
o gatilho é sempre deliberado e o cmux está vivo nesse instante, toda a verdade é
derivável na hora. Um hook só seria necessário para sobreviver a mortes inesperadas, que
estão fora do escopo.

**Consequência:** cada snapshot vale por um ciclo de uso. Não existe estado a conciliar.

### 3.2 Fato acima de intenção

**Decisão:** a fonte primária do vínculo sessão ↔ aba é `CMUX_SURFACE_ID`, lido do
ambiente do processo. O `resumeBinding` entra apenas para preencher lacunas.

**Porquê:** foi tratar o binding como fonte primária que produziu a falha descrita em §1.1.

**Hierarquia de confiança:**

| Fonte | Fornece | Natureza |
|---|---|---|
| `ps eww` → `CMUX_SURFACE_ID` | sessão ↔ aba | fato |
| `lsof -a -p <pid> -d cwd` | diretório real | fato |
| `cmux tree --all --id-format both` | estrutura, títulos, tipos | fato |
| `~/.claude/projects/**/*.jsonl` | transcript, tamanho, mtime | fato |
| `cmux surface resume get` | vínculo pretendido | **intenção — pode estar velha** |

### 3.3 Desarmar é via de mão única

**Decisão:** o `hibernate` reescreve os bindings com `auto_resume: false`; a aba que
invocou o comando é preservada.

**Porquê:** o CLI do cmux não consegue escrever `auto_resume: true` — esse campo é
privilégio do hook interno, que só o grava quando uma sessão tem atividade. Logo, não
existe "rearmar" depois. A única forma de ter uma sessão viva ao reabrir é nunca desarmar
aquela aba, e a escolha precisa acontecer no momento do `hibernate`.

**Consequência:** ao reabrir, exatamente uma sessão sobe — a de controle, de onde o
`wake` pode ser invocado como skill. A flag `--all` desarma inclusive essa.

### 3.4 Restauração preguiçosa

**Decisão:** o padrão é abas armadas e sessões dormindo. Cada uma sobe quando aberta.

**Porquê:** casa com o motivo de ter fechado. Subir tudo de volta anularia o ganho.

### 3.5 Sinalizar estagnadas sem bloquear

**Decisão:** sessões sem atividade há mais de `STALE_DAYS` (padrão: 7) são marcadas no
snapshot e destacadas no relatório, mas salvas normalmente.

**Porquê:** a curadoria é útil, mas não pode custar uma etapa interativa justamente
quando a intenção é fechar rápido.

## 4. Arquitetura

```
plugins/cmux-hibernate/
├── .claude-plugin/plugin.json
├── skills/cmux-hibernate/SKILL.md
├── scripts/
│   ├── lib/cmux_state.py
│   ├── hibernate.py
│   └── wake.py
├── tests/{unit,fixtures}
├── README.md
└── CHANGELOG.md
```

O núcleo é determinístico e vive nos scripts. A skill é um invólucro fino: documenta
quando usar e traduz o resultado. Nenhuma decisão do fluxo depende de julgamento de LLM.

### 4.1 `lib/cmux_state.py`

Responde a uma única pergunta: **qual é o estado real agora?** Cruza as fontes da §3.2 e
devolve um modelo único, consumido pelos dois comandos. É a fronteira entre "ler o mundo"
e "agir sobre ele" — nenhum outro módulo executa `ps`, `lsof` ou `cmux tree`.

Interface:

```python
ler_estado() -> Estado
# Estado: janelas > workspaces > panes > abas
# aba: uuid, ref, tipo, titulo, sessao|None, cwd|None, fonte, transcript|None, estagnada
```

### 4.2 `hibernate.py`

1. `ler_estado()`
2. Para cada aba com sessão, exceto a de controle: `cmux surface resume set` com o `cwd`
   real, o checkpoint e o comando de resume.
3. Grava `snapshot.json` e `INVENTARIO.md`.
4. Aplica retenção (mantém os 5 últimos).
5. Imprime o resumo.

Flags: `--dry-run` (não muta), `--all` (desarma inclusive a de controle),
`--stale-days N`.

### 4.3 `wake.py`

1. Carrega o snapshot mais recente (ou `--snapshot <path>`).
2. `ler_estado()`.
3. Compara e age conforme o modo:

| Modo | Ação |
|---|---|
| padrão | Relatório; corrige vínculos divergentes |
| `--up <alvo\|all>` | Sobe as sessões indicadas via `surface.send_text` |
| `--rebuild` | Recria janelas/workspaces/abas ausentes via `new-workspace --layout` |

Executável direto no terminal, sem depender de sessão Claude — precondição do cenário de
resgate, em que nenhuma existe.

Opções: `--snapshot <path>` (usa um snapshot específico em vez do mais recente),
`--max-age N` (sobrescreve `MAX_SNAPSHOT_AGE`).

## 5. Formato do snapshot

`~/.local/state/cmux-hibernate/<ISO-timestamp>/snapshot.json`

```json
{
  "gerado_em": "2026-08-04T14:22:31",
  "metodo": "CMUX_SURFACE_ID (processo)",
  "stale_days": 7,
  "aba_de_controle": "<surface-uuid>",
  "janelas": [{
    "uuid": "...", "ref": "window:1",
    "workspaces": [{
      "uuid": "...", "nome": "projeto-alfa",
      "panes": [{ "uuid": "...", "abas": [{
        "uuid": "...", "ref": "surface:27", "tipo": "terminal",
        "titulo": "cloud-migration: execute PR-0 baseline proof",
        "sessao": "4f8b05f3-...", "cwd": "/Users/.../Lass/projeto-alfa",
        "fonte": "processo",
        "transcript": { "path": "...jsonl", "kb": 21312, "mtime": "2026-08-04T09:11:02" },
        "estagnada": false
      }]}]
    }]
  }]
}
```

Não há campo que afirme estado volátil ("estava rodando"). Tudo que envelhece é derivado
na leitura. `INVENTARIO.md` acompanha como versão legível, para reconstrução manual sem
agente.

## 6. User flow

### Caminho principal

1. Máquina no limite → `/cmux-hibernate:hibernate` de qualquer sessão.
2. Relatório em ~5 s: total, estagnadas destacadas, abas desarmadas, aba preservada,
   caminho do snapshot.
3. `Cmd+Q`.
4. Reabrir: estrutura volta, nada sobe além da aba de controle.
5. Trabalhar: cada aba acorda ao ser aberta. Na maioria dos dias o `wake` não é usado.

### Caminhos secundários

- **Conferir:** `/cmux-hibernate:wake` → relatório de integridade; corrige o que divergir.
- **Acordar em lote:** `wake --up all`, ou `--up <workspace>` para um recorte.
- **Resgate:** `wake.py --rebuild` no terminal, quando o cmux abre vazio.

## 7. Casos de borda

| Situação | Comportamento |
|---|---|
| Sessão sem transcript | Registrada como não-restaurável; nenhum comando de resume gerado |
| Transcript em slug divergente | Resolver pelo `cwd` interno do `.jsonl`, não pelo nome do diretório |
| Aba sem sessão (shell) | Entrada de terminal simples, sem comando |
| Aba não materializada | `surface.send_text` enfileira (`queued: true`); executa ao abrir |
| Estrutura já restaurada | Corrige apenas vínculos; nunca cria aba de sessão já viva |
| Snapshot mais velho que `MAX_SNAPSHOT_AGE` (padrão: 3 dias) | Avisa a idade e exige confirmação antes de aplicar. Parâmetro distinto de `STALE_DAYS`, que qualifica sessões, não snapshots |
| cmux fora do ar | Falha com mensagem clara, sem efeito parcial |
| Dois processos com o mesmo `session_id` | Reporta como anomalia; não desarma nem sobe |

Anti-duplicação usa **session id** como chave — nunca título ou posição. Títulos mentem:
uma aba chamada "Painel Gamma" pode hospedar sessão do `projeto-alfa`.

## 8. Testes

**Unit**, sobre fixtures gravadas de `cmux tree`, `ps eww` e `lsof`:

- parsing da árvore (janelas, workspaces, panes, abas, browser, markdown)
- extração de `CMUX_SURFACE_ID` e resolução de `cwd`
- detecção de estagnação por `mtime`
- resolução de transcript quando o slug do diretório diverge do `cwd`

**Regressão obrigatória:** binding aponta para a sessão A enquanto o processo roda a
sessão B → o snapshot deve registrar **B**. É a falha exata que escondeu 7 conversas.

**Integração:** dry-run contra o cmux vivo; o plano gerado precisa bater com o estado
observado, sem mutação.

## 9. Incertezas a validar

1. **Abrir aba com `auto_resume: false`** — o cmux oferece restaurar ou devolve shell?
   Só se verifica fechando e reabrindo. O desenho não depende disso (o `wake` dispara de
   qualquer forma), mas se oferecer, o caminho feliz dispensa o `wake`.
2. **Limite de `send_text` enfileirado** — quantos comandos o cmux mantém na fila e por
   quanto tempo, com dezenas de abas desarmadas.
3. **`new-workspace --layout` e proporção de split** — o CLI não expõe a proporção real;
   `--rebuild` reconstrói splits de forma aproximada. Documentar como limitação conhecida.

## 10. Fora de escopo

- Suporte a outros multiplexadores.
- Restauração de processos não-Claude (servidores, watchers) rodando nas abas.
- Sincronização entre máquinas.
- Qualquer automação disparada sem intenção explícita do usuário.
