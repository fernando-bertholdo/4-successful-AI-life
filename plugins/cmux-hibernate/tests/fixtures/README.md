# Fixtures

Saídas reais do ambiente, **sanitizadas**, usadas pelos testes unitários.

| Arquivo | Origem | Conteúdo |
|---|---|---|
| `tree.txt` | `cmux tree --all --id-format both` | 4 janelas, 12 workspaces, 37 abas |
| `ps-eww.txt` | `ps eww` por processo Claude | 33 processos com `CMUX_SURFACE_ID` |

## Por que são sanitizadas

Este repositório é público. A captura crua carrega nomes de cliente, títulos de
conversa e caminhos de projeto reais. `sanitize.py` substitui tudo por equivalentes
sintéticos e preserva exatamente o que os testes exercitam: hierarquia, formato de
UUID, tipos de surface e presença de sessão.

A substituição é **injetora** — identificadores distintos no cru continuam distintos
no sanitizado. Sem isso, os testes de vínculo sessão↔aba perderiam o sentido.

## Regenerar

```bash
./capture.sh          # grava em .raw/ (não versionado)
python3 sanitize.py   # gera as fixtures publicáveis
```

Rode com o cmux aberto e várias sessões ativas — quanto mais rica a captura, melhor a
cobertura. Depois, confirme que nada real sobrou:

```bash
grep -inE 'seu-usuario|seu-host|/Documents/|nome-de-projeto' tree.txt ps-eww.txt
```

`.raw/` está no `.gitignore` e **nunca deve ser commitado**.
