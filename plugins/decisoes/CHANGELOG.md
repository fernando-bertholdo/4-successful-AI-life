# Changelog

## [0.1.0] — 2026-10-04

### Added
- Primeira versão no marketplace. O mod foi escrito e testado numa sessão de 04/10/2026 e
  existia só como pasta temporária; entra aqui sem mudança de comportamento.
- A ferramenta `registrar_decisao`, a instrução no prompt de sistema, a captura das linhas
  marcadas no texto, a faixa acima do prompt, o painel `/decisoes`, o cadastro das sessões
  no armazenamento compartilhado, a navegação para a aba de outra sessão no cmux (ou a
  retomada numa aba nova) e os dois botões de pouso.
- Sete testes em `hooks/register.test.ts`, rodados com `claude plugin test`. Medido em
  04/10/2026 no Claude Code 2.1.289: 7 pass, 0 fail; `claude plugin validate` sem aviso.
- Diferenças em relação à pasta de origem: o `plugin.json` ganha autor, repositório, licença e
  palavras-chave (o `validate` avisava a falta de autor), e as fixtures dos testes usam um
  workspace e um diretório de nome neutro no lugar dos nomes de um projeto real.
