# cmux-hibernate

Feche o cmux quando quiser — para reiniciar a máquina ou liberar memória — e reabra com
o ambiente intacto e leve.

## O problema

Dezenas de abas com sessões do Claude Code consomem memória. Fechar o cmux é arriscado
por dois motivos:

1. **O `resumeBinding` envelhece.** Ele registra a *intenção* gravada por um hook, não o
   processo real, e fica desatualizado quando uma sessão passa a gravar sob outro id.
   Num ciclo real de fechar e reabrir, isso escondeu 7 conversas — uma delas com 5,2 MB.
2. **Reabrir sobe tudo de uma vez**, recriando exatamente o peso que motivou o fechamento.

## Como funciona

`hibernate` lê o estado **dos processos** (`CMUX_SURFACE_ID`, `lsof`), não dos metadados
do cmux, e reescreve cada binding com o diretório correto e `auto_resume: false`. Você
fecha; ao reabrir, a estrutura volta e nada sobe. Cada aba acorda quando você a abre.

O snapshot é um **retrato datado de uso único** — não há registro contínuo para conciliar
nem lista de sessões mortas para limpar. Os 5 últimos ficam em
`~/.local/state/cmux-hibernate/`; os demais somem sozinhos.

## Uso

```bash
python3 scripts/hibernate.py            # dry-run: mostra o que faria
python3 scripts/hibernate.py --apply    # desarma e grava o snapshot
# Cmd+Q, reabrir o cmux
python3 scripts/wake.py                 # confere
python3 scripts/wake.py --up all        # sobe tudo (opcional)
python3 scripts/wake.py --rebuild       # recria workspaces ausentes
```

A aba de onde o `hibernate` roda é preservada: é a única sessão viva ao reabrir, e de
onde você pode pedir a conferência. `--all` desarma inclusive ela.

## Limitações conhecidas

- **Splits aproximados no `--rebuild`.** O CLI do cmux não expõe a proporção real dos
  painéis; a reconstrução assume 50/50. Afeta apenas workspaces com painel dividido, e
  só no modo de resgate.
- **Sessões sem transcript não voltam.** Se o `.jsonl` não existe mais em disco, não há o
  que retomar — o comando diz isso explicitamente em vez de tentar.
- **Específico do cmux.** Depende do CLI e de `CMUX_SURFACE_ID`.

## Desenvolvimento

```bash
bash tests/run-tests.sh              # 37 testes, somente stdlib
tests/fixtures/capture.sh            # recaptura o ambiente (grava em .raw/)
python3 tests/fixtures/sanitize.py   # gera as fixtures publicáveis
```

As fixtures são sanitizadas automaticamente porque este repositório é público. Ver
`tests/fixtures/README.md`.

## Requisitos

Python 3.9+ (somente stdlib), macOS com cmux instalado.
