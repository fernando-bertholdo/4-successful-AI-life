# cmux-hibernate

Feche o cmux quando quiser — para reiniciar a máquina ou liberar memória — e reabra com
o ambiente intacto e leve.

## O problema

Dezenas de abas com sessões do Claude Code consomem memória. Fechar o cmux é arriscado
por dois motivos:

1. **Reabrir sobe tudo de uma vez.** O cmux relança o Claude de cada aba que ele guardou
   como ativa, recriando exatamente o peso que motivou o fechamento.
2. **O que o cmux mostra não é o que ele usa.** O `resumeBinding` que o CLI devolve
   registra uma intenção gravada por um hook e envelhece; e, no cmux 0.65.2, reescrevê-lo
   com `cmux surface resume set` é recusado em silêncio, com o CLI respondendo `OK`. Num
   ciclo real, em 31/10/2026, isso deixou 11 de 13 abas "desarmadas" subirem sozinhas.

## Como funciona

`hibernate` monta o inventário pelos **processos** (`CMUX_SURFACE_ID`, `lsof`) e pelo
**autosave do cmux** (`~/Library/Application Support/cmux/session-com.cmuxterm.app.json`),
que é o arquivo que a restauração lê. Para cada aba, ele planeja uma ação e, com
`--apply`:

- **encerra com SIGTERM** o `claude` ocioso da aba. A memória sai na hora, e o hook
  `SessionEnd` tira a aba do autosave. Ele não usa SIGKILL e pula a aba ocupada;
- **limpa o registro** da aba armada sem processo (`cmux rpc surface.resume.clear`);
- **confere no autosave regravado** que nenhuma aba-alvo vai subir. Só então diz "Pode dar
  Cmd+Q".

A aba de onde o comando roda continua armada: é a única que pode subir ao reabrir. As
outras voltam sem o Claude, e você retoma cada uma quando quiser. Na prova de 09/11/2026,
no cmux 0.65.2, nem ela subiu; o `wake.py` aponta isso, e `claude --resume <id>` a retoma.

`wake` compara o snapshot do último `--apply` com o estado real, aba a aba: dormindo,
subiu sozinha (o desarme falhou), acordada por você (com a hora), armada para o próximo
fechamento, ausente ou sem transcript.

O snapshot é um **retrato datado de uso único**, com o plano e o resultado conferido de
cada aba. Os 5 últimos `--apply` ficam em `~/.local/state/cmux-hibernate/`; os demais
somem sozinhos. O dry-run grava só `ultimo-dry-run/`, fora dessa conta.

## Uso

```bash
python3 scripts/hibernate.py            # dry-run: mostra o plano por aba
python3 scripts/hibernate.py --apply    # encerra as ociosas e confere
# Cmd+Q, esperar uns 10 s, reabrir o cmux
python3 scripts/wake.py                 # confere
python3 scripts/wake.py --up <ws>       # retoma um workspace (ou all)
python3 scripts/wake.py --rebuild       # recria workspaces ausentes
```

`--all` inclui a aba de onde o `hibernate` roda. `--surface <aba>` planeja uma aba só,
pelo uuid ou pela ref `surface:N` do `cmux tree`; as outras herdam no snapshot o plano do
último `--apply`. `--estado DIR` troca o diretório dos snapshots, nos dois scripts.

O `hibernate` nunca encerra a sessão que o roda. Se ela é alvo (com `--all`, ou com
`--surface` na própria aba), sai como PENDENTE e pede `/exit`: o `SessionEnd` do `/exit`
desarma a aba. Para hibernar a própria aba sem `/exit`, rode o comando de fora dela.

Antes de "Pode dar Cmd+Q", o `hibernate` relê o autosave (um save posterior ao início do
comando; sem mudança nenhuma, o cmux pode levar até 60 s para regravar) e roda um `ps`
novo: nenhum painel armado e nenhum `claude` vivo fora da aba de controle.

Códigos de saída do `hibernate`: 0 no caminho normal; 1 quando alguma aba-alvo não foi
conferida desarmada (no dry-run, só com `--surface`); 2 em erro de leitura do cmux ou de
argumento; 3 quando só falta a sessão que roda o comando sair com `/exit`. Do `wake`: 0
sem falha, 1 com alguma FALHA, 2 em erro.

O comando de retomada (`--up` e `INVENTARIO.md`) é
`claude --resume <sessão> --dangerously-skip-permissions`, o modo em que as sessões deste
fluxo rodam. Quem usa o Claude Code com pedidos de permissão deve tirar a flag ao colar o
comando.

## Limitações conhecidas

- **Depende da mecânica do cmux 0.65.2.** A regra de quem sobe sozinho (o `agent` do
  painel, ou um binding `agent-hook` com `autoResume: true`) e o `rpc` de reserva, cujo
  parâmetro `agent_session_ended` é contrato interno do hook do cmux, foram lidos no
  código dessa versão e medidos no autosave. Outra versão pode mudar os dois.
- **Medido no Cmd+Q de 09/11/2026:** nenhuma aba hibernada subiu. A aba de controle,
  armada no autosave do quit, também não subiu: é o restore do cmux 0.65.2, e o
  `wake.py` aponta a falha. O que uma aba encerrada mostra ao ser aberta ainda não foi
  medido.
- **Aba ocupada é pulada, e o critério é heurístico:** transcript escrito há menos de
  60 s (o da sessão ou um `.jsonl` novo do mesmo projeto) ou o registro do hook do cmux
  dizendo que há turno. Uma ferramenta longa sem registro no hook passa por ociosa.
- **Restore atrasado e clique na aba não se distinguem.** O `wake` usa a hora em que o
  processo nasceu: até 60 s depois do cmux é "subiu sozinha"; depois, "acordada", ou
  "suspeita" quando o `hibernate` não tinha conferido a aba. O ambiente não ajuda:
  `CMUX_AGENT_RESUME_LAUNCH=1` sai de todo `claude --resume <id>` pelo wrapper do cmux.
- **Splits aproximados no `--rebuild`.** O CLI do cmux não expõe a proporção real dos
  painéis; a reconstrução assume 50/50.
- **Sessões sem transcript não voltam.** Se o `.jsonl` não existe mais em disco, não há o
  que retomar — o comando diz isso explicitamente em vez de tentar.
- **Específico do cmux no macOS.** Depende do CLI, de `CMUX_SURFACE_ID` e de `ps`.

## Desenvolvimento

```bash
bash tests/run-tests.sh              # suíte de testes, somente stdlib
tests/fixtures/capture.sh            # recaptura o ambiente (grava em .raw/)
python3 tests/fixtures/sanitize.py   # gera as fixtures publicáveis
```

Os testes do `hibernate.py` rodam contra um cmux falso (`tests/unit/cmux_falso.py`), que
reproduz o SIGTERM, o autosave regravado e o `OK` que não pega. As fixtures são
sanitizadas ou inventadas, porque este repositório é público. Ver
`tests/fixtures/README.md`.

## Requisitos

Python 3.9+ (somente stdlib), macOS com cmux instalado.
