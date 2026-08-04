# Changelog

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
