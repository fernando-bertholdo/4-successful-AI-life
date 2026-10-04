# Changelog

## [0.2.0] — 2026-10-04

### Added
- `hibernate.py --surface <aba>` desarma uma aba só, pedida pelo uuid (o formato do
  `CMUX_SURFACE_ID`, em qualquer caixa) ou pela ref `surface:N`. Pedir a aba pelo nome vence
  a preservação da aba de controle: é o que deixa uma sessão hibernar a própria aba, como no
  revezamento de sessão. A sessão que aparece em mais de uma aba continua pulada.
- No dry-run com `--surface`, a saída diz qual aba seria desarmada.
- A `SKILL.md` e o `README.md` do plugin dizem como pedir uma aba só.
- `--surface` e `--all` são mutuamente exclusivos. Aba que não casa, ou casa mais de uma vez,
  e aba sem sessão Claude Code saem com erro e código 2, sem gravar snapshot.
- Sete testes em `test_bindings.py` (`TestUmaAba`). Medido em 04/10/2026: 71 testes OK.

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
