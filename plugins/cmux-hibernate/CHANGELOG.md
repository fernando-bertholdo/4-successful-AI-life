# Changelog

## [0.3.0] — 2026-10-31

### Fixed
- **O desarme não tinha efeito no cmux 0.65.2, e o `hibernate.py` dizia "Pode dar Cmd+Q"
  mesmo assim.** O `cmux surface resume set --source agent-hook` sem `auto_resume: true` é
  recusado quando a aba já tem um binding `agent-hook` confiável, e o CLI imprime `OK`; o
  `desarmar()` aceitava esse `OK`. Em 31/10/2026, 11 das 13 abas "desarmadas" subiram
  sozinhas ao reabrir (TECH-1307). O `desarmar()` e a checagem `"OK" in saida` saem.
- **O `wake.py` respondia "Nada a corrigir" com abas que deviam dormir de pé**, porque só
  sabia "rodando", "dormindo" e "ausente", e o snapshot não guardava o plano.
- O dry-run gravava snapshot e rodava a retenção dos 5: empurrava para fora os snapshots
  de `--apply`, e o `wake.py` escolhia o mais recente, fosse qual fosse.
- Aba com sessão e sem processo ficava fora do snapshot e do `INVENTARIO.md`: hibernar
  duas vezes seguidas apagava do inventário quem já dormia.
- O `wake.py` quebrava com `EOFError` no `input()` quando rodava sem terminal interativo,
  que é como o agente o chama, e o snapshot tinha mais de 3 dias.

### Changed
- `hibernate.py --apply` **encerra com SIGTERM o `claude` ocioso** de cada aba-alvo. A
  memória sai na hora, e o hook `SessionEnd` tira do autosave do cmux o `agent` e o binding
  da aba. O pid é relido antes do sinal (precisa ser um `claude`, não o daemon de fundo,
  com a variável `CMUX_SURFACE_ID` daquela aba), a espera é de até 10 s e não há SIGKILL.
  Aba com `claude` vivo sem o id da sessão no argv também leva o pid, para não virar uma
  limpeza de registro com o processo de pé. A aba armada sem processo
  (um restore que falhou) é limpa por `cmux rpc surface.resume.clear` com
  `agent_session_ended: true`, que também é a reserva quando o `SessionEnd` não limpa.
  Esse parâmetro é contrato interno do hook do cmux, e por isso só vale conferido.
- **Nenhum sucesso sem conferência.** O resultado de cada aba só é "verificado" quando o
  autosave (`~/Library/Application Support/cmux/session-com.cmuxterm.app.json`), regravado
  depois da ação, diz que ela não sobe: sem `terminal.agent` e sem binding `agent-hook` com
  `autoResume: true`. "Pode dar Cmd+Q" só sai com todas as abas-alvo verificadas, junto com
  "espere uns 10 s antes de reabrir"; senão a saída lista as que falharam e o código é 1.
- O plano tem uma ação por aba: encerrar, limpar, dormindo, pular ou controle. São puladas
  a aba ocupada (transcript escrito há menos de 60 s, ou o registro do hook do cmux com
  turno, pedido de permissão ou trabalho de fundo), a sessão em mais de uma aba e a sessão
  que roda o próprio comando (com `--all` ou `--surface` na própria aba).
- O inventário junta três fontes: os processos, o autosave do cmux (aba armada sem
  processo) e o snapshot anterior (quem já dormia; o da 0.2.0, sem tipo, também serve).
- O snapshot diz o `tipo` (`apply` ou `dry-run`), o escopo, as versões do plugin e do
  cmux, e o plano com o resultado de cada aba: método, verificado ou não, e a hora em UTC.
  O dry-run vai para `ultimo-dry-run/`, sobrescrito a cada vez e fora da retenção.
- `wake.py` lê o último `--apply` e classifica cada aba contra o plano: dormindo,
  controle, subiu sozinha (processo nascido até 60 s depois do cmux, pelo `ps -o lstart`),
  acordada por você às HH:MM BRT, não dormiu (processo anterior ao snapshot) e armada
  (sem processo, mas registrada no autosave). "Nada a corrigir" só sai sem subiu sozinha,
  não dormiu, armada nem ausente. Sai a promessa "sobem ao abrir a aba"; o `--up` também
  retoma as armadas sem processo. Rodado antes do Cmd+Q, ele avisa que a conferência que
  vale é a de depois. O snapshot sem tipo só entra com `--snapshot`.
- `--estado DIR` nos dois scripts troca o diretório dos snapshots.
- A `SKILL.md` e o `README.md` descrevem o fluxo novo; o que só a reabertura prova fica
  marcado como a confirmar. O `plugin.json` passa o `repository` para
  `fernando-bertholdo/nbstack` e deixa de dizer que o plugin libera memória sem encerrar
  nada.
- Um erro no meio do `--apply` (um `rpc` que levanta, por exemplo) não derruba o script
  depois dos SIGTERMs: os alvos sem resultado ficam não verificados, o snapshot é gravado
  e a saída é 1, sem "Pode dar Cmd+Q".
- **Conferência global antes do Cmd+Q.** Um autosave regravado depois do início do
  comando (até 75 s de espera, porque sem mudança o cmux pode pular o save por 60 s) e um
  `ps` novo: nenhum painel armado e nenhum `claude` vivo fora da aba de controle. Cada
  alvo, inclusive o que já dormia, é conferido nessa releitura; painel que some do
  autosave, ou um autosave sem painel de terminal, não confere.
- Com vários `claude` na mesma aba, vale o que não descende de outro `claude` da aba, e a
  aba só passa sem `claude` nenhum depois do SIGTERM.
- Antes do SIGTERM, o binário vem do argv (`ps -o args=`) e o instante de nascimento do
  processo tem de ser o da leitura inicial, o que barra pid reusado.
- "Ocupada" olha também o `.jsonl` novo do mesmo projeto (depois de um `/clear`) e o
  registro do hook achado pela aba; `error` só segura a aba se for recente.
- O snapshot do `--apply` é gravado antes do primeiro sinal e regravado num `finally` que
  cobre interrupção; `concluido` diz se o `--apply` chegou ao fim.
- Com `--surface`, as outras abas herdam o plano do último `--apply` (`herdado: true`).
- A sessão que roda o comando nunca é encerrada: alvo dela sai como PENDENTE, com código 3
  e o pedido de `/exit`.
- O `wake.py` sai com 1 quando há FALHA: subiu sozinha, não dormiu, suspeita (nasceu tarde
  numa aba que o hibernate não conferiu) e a aba de controle que não subiu. Nos primeiros
  120 s depois de o cmux abrir, ele pede para rodar de novo.
- Uma versão do cmux diferente da 0.65.2 gera aviso. O `INVENTARIO.md` cita o `cwd` com
  `shlex.quote`.
- **A fixture `ps-eww.txt` saía com o ambiente real**: o token do socket do cmux, o argv
  em base64, o `TMPDIR` e o serviço do launchd, publicados desde a 0.1.0. A linha passou a
  ser reconstruída por lista de permissão, e `test_sanitize.py` reprova ambiente real em
  qualquer fixture versionada.
- **Aviso sobre `claude` vivo no cmux sem `CMUX_SURFACE_ID`.** O plugin só enxerga uma
  sessão pela variável, então uma aberta enquanto o socket recusava clientes ficava fora
  do plano e do inventário, e caía no Cmd+Q sem aviso (caso real de 09/11/2026). O
  dry-run e o `--apply` agora a listam, com o pid, o `cwd` e o `claude --resume <id>`
  (id do argv ou do `~/.claude/sessions/<pid>.json`), e o snapshot a guarda em `sem_aba`.
  É aviso, não trava: o Cmd+Q continua liberado, com um lembrete logo antes. "No cmux"
  é o `__CFBundleIdentifier=com.cmuxterm.app` que o app passa aos filhos.
- Testes: de 83 para 218, medidos em 31/10/2026 (210) e 09/11/2026 (218). Os do `main()` rodam contra um cmux falso
  (`tests/unit/cmux_falso.py`), que reproduz o SIGTERM, o autosave regravado e o `OK` que
  não pega; as fixtures novas (`autosave.json`, `claude-hook-sessions.json`) são
  inventadas.

### Em aberto
- A primeira reabertura com a 0.3.0: que só a aba de controle sobe, e o que a aba
  encerrada mostra ao ser aberta. Só o Cmd+Q prova.

## [0.2.0] — 2026-10-04

### Added
- `hibernate.py --surface <aba>` desarma uma aba só, pedida pelo uuid (o formato do
  `CMUX_SURFACE_ID`, em qualquer caixa) ou pela ref `surface:N`. Pedir a aba pelo nome vence
  a preservação da aba de controle: é o que deixa uma sessão hibernar a própria aba, como no
  revezamento de sessão. A sessão que aparece em mais de uma aba continua pulada.
- No dry-run com `--surface`, a saída diz qual aba seria desarmada.
- A `SKILL.md` e o `README.md` do plugin dizem como pedir uma aba só.
- `--surface` e `--all` são mutuamente exclusivos. Alvo vazio (um `$CMUX_SURFACE_ID` sem
  valor), aba que não casa ou casa mais de uma vez, e aba sem sessão Claude Code saem com
  código 2, antes de gravar snapshot; a mensagem diz quantas abas casaram.
- Com `--surface`, a saída é 1 quando a aba pedida não é desarmada, ou não seria no dry-run
  (sessão em mais de uma aba, desarme que falhou), e o "Pode dar Cmd+Q" não aparece.
- O snapshot não chama de aba de controle a aba que o `--surface` desarmou.
- Dezenove testes: dez em `test_bindings.py` (`TestUmaAba`) e nove no novo
  `test_hibernate_main.py`, que roda o `main()` sem cmux. Medido em 04/10/2026: 83 testes OK;
  com `if args.surface:` no lugar de `if args.surface is not None:`, 1 falha (alvo vazio).

## [0.1.2] — 2026-10-03

### Changed
- `test_carimbo.py`: a classe `TestGravar` fixa o fuso do processo (`FusoFixo`, `Asia/Tokyo`).
  Antes ela herdava o fuso do host, e sob UTC a mutação que grava a hora local com `Z`
  coincidia com a certa e passava a suíte. Medido sob `TZ=UTC`: com a mutação, 1 falha,
  diferença de `32399.x` s (9 h menos a fração do segundo; `32399.02` na medição) contra o
  limite de 2 s; sem ela, 64 testes OK. Só teste, o plugin não muda de comportamento.

## [0.1.1] — 2026-10-03

### Fixed
- O carimbo de máquina sai em UTC com `Z`: `gerado_em` no `snapshot.json` e o nome do
  diretório do snapshot (`2026-10-03T22-30-00Z`). Até aqui os dois saíam na hora local do
  host, sem zona.
- A hora mostrada a gente vai no horário de Brasília, com a zona escrita: `**Gerado:**`
  no `INVENTARIO.md` (`03/10/2026 19:30 BRT (2026-10-03T22:30:00Z)`) e a linha
  "Snapshot de" do `wake.py`.
- O `wake.py` continua lendo os snapshots gravados pela 0.1.0, sem zona, como hora local
  do host. A escolha do mais recente e a retenção ordenam pelo instante, não pelo nome:
  nome em hora local e nome em UTC não se comparam como texto, e num host à frente de UTC
  a ordem por nome pode escolher o antigo, quando o intervalo entre os dois snapshots é
  menor que o adiantamento do fuso. A retenção só conta e só apaga diretório
  cujo nome é carimbo de snapshot: um diretório de outro nome, posto ali à mão, fica.
- Novo `lib/carimbo.py`, com os testes de cada formato.

## [0.1.0] — 2026-08-04

### Added
- `hibernate.py`: retrata o estado real, desarma os bindings preservando a aba de
  controle e grava snapshot + inventário em `~/.local/state/cmux-hibernate/`.
- `wake.py`: compara o snapshot com o estado real; `--up` sobe sessões sob demanda e
  `--rebuild` recria workspaces ausentes. Executável sem sessão Claude.
- `lib/cmux_state.py`: deriva o vínculo sessão↔aba de `CMUX_SURFACE_ID`, tratando o
  `resumeBinding` apenas como complemento.
- Skill `cmux-hibernate` e registro no marketplace.
- 37 testes sobre fixtures reais sanitizadas, incluindo regressão para binding
  desatualizado e para sessão duplicada.

### Notas de design
- Sem hooks e sem registro contínuo: o estado é derivado no momento do comando, com o
  cmux vivo. Um registro que afirma "estas sessões existem" apodrece; um retrato datado
  de uso único, não.
- Desarmar é via de mão única — o CLI do cmux não escreve `auto_resume: true`, que é
  privilégio do hook interno. Por isso a aba de controle é escolhida no `hibernate`, e
  não depois.
- As fixtures são sanitizadas por script, não à mão: o repositório é público e revisar
  fixture a olho é o tipo de etapa que passa batido.

### Em aberto
- Comportamento do cmux ao abrir uma aba com `auto_resume: false`: oferece restaurar ou
  devolve shell? Só se verifica fechando e reabrindo. Se oferecer, o `--up` passa a ser
  opcional no caminho feliz. Ver "Validação manual" no plano de implementação.
