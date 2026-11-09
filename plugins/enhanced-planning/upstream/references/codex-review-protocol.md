# Codex Review Protocol

Protocolo de revisao cruzada Codex em 2 fases. Executar **1 revisao por PR/deliverable** com meta-avaliacao.

**A revisão Codex é opcional.** Ela só entra no plano quando o `/codex:rescue` está disponível (pré-condição de instalação, ver "Quando Pular"), a Checagem de Acesso (abaixo) passa e o usuário confirma a inclusão. Faltando qualquer uma das três, o plano não traz a seção, e o pulo é registrado (ver "Quando Pular").

## Como Invocar

**A revisao Codex DEVE ser executada via `/codex:rescue`.** Invocar antes de montar o prompt, passando `--effort xhigh` na chamada.

**Effort recomendado:** passar a flag `--effort xhigh` ao invocar `/codex:rescue`.

> Exemplo de fluxo: ao chegar no passo "Invocar Codex", o agente deve chamar `/codex:rescue --effort xhigh` com o prompt abaixo e aguardar o resultado.

## Pre-requisitos

- PR/deliverable com criterios de aceite 100% marcados
- Verificacao cruzada de docs completa
- Plugin `codex` instalado: `/codex:rescue` disponível na sessão (pré-condição de instalação, ver "Quando Pular")
- Acesso ao Codex confirmado pela Checagem de Acesso, rodada ao completar o PR
- Inclusão da revisão no plano confirmada pelo usuário (Step 2 da skill)

## Checagem de Acesso

Um comando decide o acesso ao serviço (a instalação do plugin é pré-condição, tratada em "Quando Pular"). Ele faz uma chamada mínima ao serviço:

```bash
codex exec --skip-git-repo-check "Responda apenas: ok" </dev/null
```

- Exit `0`: o Codex respondeu, o acesso existe.
- Qualquer outro exit, inclusive `127` (binário ausente) e `124` (o `timeout` cortou o comando): pular a revisão. Estouro do tempo da ferramenta que roda o comando também pula: sem resposta, não há acesso confirmado.

O `</dev/null` fecha o stdin e não é enfeite: com stdin em pipe aberto o `codex exec` fica lendo (`Reading additional input from stdin...`) e nunca chega ao serviço, e a checagem trava em vez de responder, com um falso "sem acesso" no fim. Medido com o `codex-cli 0.147.0` e `CODEX_HOME` vazio, sem credencial: com `</dev/null`, exit 1 em 16 s; com stdin em pipe aberto, `timeout 25` o cortou com exit 124 (TECH-907, 01/10/2026; a revisão da TECH-830 mediu o mesmo: exit 1 em 15 s e exit 124 com `timeout 45`). O caminho com credencial não foi medido. O comando não prescreve `timeout`: ele é do GNU coreutils e pode faltar no macOS, onde sairia com exit 127 e pularia por engano.

A Checagem deixa rastro: sem `--ephemeral`, o `codex exec` grava uma sessão em `~/.codex/sessions` a cada execução. Medido com o `codex-cli 0.147.0` e `CODEX_HOME` vazio, sem credencial (TECH-907, 01/10/2026): sem a flag, exit 1 e 1 arquivo em `sessions/`; com `--ephemeral`, exit 1 e nenhum arquivo; com uma flag inventada, exit 2. A flag fica fora do comando de propósito: ela existe no 0.147.0, mas um `codex` que não a conheça a trataria como flag desconhecida (exit 2) e a Checagem pularia por engano, o mesmo falso "sem acesso" do `</dev/null` ausente. Com credencial, não medido.

`codex --version`, `codex login status` e o `ready` do `/codex:setup` não decidem: medem o binário e a credencial salva, não o acesso ao serviço. Medição da TECH-830, em 30/09/2026: `codex --version` saiu com exit 0 e `codex login status` respondeu `Logged in using ChatGPT`, e o `codex exec` do comando acima saiu com exit 1 e `401 Unauthorized`. Com a checagem pelo binário, esse Codex valia como disponível e a revisão quebrava no meio. Do `ready`, a leitura do código do plugin 1.0.4 (lido, não executado: o campo `ready` de `buildSetupReport`, em `scripts/codex-companion.mjs`, e `getCodexAuthStatusFromClient`, em `scripts/lib/codex.mjs`) mostra Node, binário e conta lida com `account/read` e `refreshToken: false`, sem renovar o token: é a mesma classe do `codex login status`. As funções vêm citadas pelo nome porque o número de linha anda na primeira atualização do plugin.

Rodar a checagem em dois momentos: ao montar o plano (ela decide se a pergunta ao usuário chega a ser feita) e ao completar cada PR (o acesso muda entre sessões, por exemplo com a cota esgotada).

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

A revisao Codex e pulada quando qualquer uma destas tres condicoes vale:
- O usuário não confirma a inclusão no plano (Step 2 da skill), ou pede para pular depois
- O `/codex:rescue` não consta entre os comandos disponíveis na sessão (pré-condição de instalação, abaixo), conferido antes da Checagem
- A Checagem de Acesso sai com exit diferente de 0. Medido: credencial expirada (`401 Unauthorized`, exit 1, TECH-830, 30/09/2026) e binário ausente (exit 127, `bash -c 'inexistente "ok"'`, 01/10/2026). Cota esgotada: esperado, não medido

**Pré-condição de instalação, conferida antes da Checagem e fora da decisão de acesso.** O `/codex:rescue` só existe com o plugin `codex` instalado, e a Checagem não enxerga o plugin: ela só chama o `codex exec`. Com o `codex` acessível e sem o plugin, a Checagem passaria e a revisão quebraria no meio, na hora de invocar o `/codex:rescue`. Por isso a pré-condição se confere à parte, antes da Checagem e nos mesmos dois momentos em que ela roda: o `/codex:rescue` consta entre os comandos disponíveis na sessão. Sem ele, a seção 8 não entra no plano (a pergunta ao usuário não é feita) e o pulo é registrado como `pulada (plugin codex ausente)`. O `/codex:setup` serve para instalar o plugin; o `ready` dele não prova acesso (ver "Checagem de Acesso"): passar nele não dispensa a Checagem.

Texto do registro: `Revisao Codex: pulada ([motivo])`. Quando foi a pré-condição, o motivo é `plugin codex ausente`; quando foi a Checagem, o motivo cita o exit dela, por exemplo `pulada (sem acesso: codex exec saiu com exit 1)`. Onde registrar: o pulo do plano, decidido ao montá-lo, vai numa nota logo abaixo da Tabela de Progresso (a tabela é por slice e não tem linha para ele); o pulo de um PR, decidido ao completá-lo (pela pré-condição ou pela Checagem), vai na coluna Notas da linha do slice.
