# Changelog

## [0.1.0] — 2026-10-04

### Added
- Primeira versão no marketplace. O mod foi escrito e testado numa sessão de 04/10/2026 e
  existia só como pasta temporária; as mudanças para publicá-lo estão no fim desta lista.
- A ferramenta `registrar_decisao`, a instrução no prompt de sistema, a captura das linhas
  marcadas no texto, a faixa acima do prompt, o painel `/decisoes`, o cadastro das sessões
  no armazenamento compartilhado, a navegação para a aba de outra sessão no cmux (ou a
  retomada numa aba nova) e os dois botões de pouso.
- A opção `dono` (`userConfig`): como os textos que o agente lê chamam quem decide, com o
  artigo ("o Fernando", "a Ana"); vazia, vale "o usuário".
- Nove testes em `hooks/register.test.ts`, rodados com `claude plugin test`. Medido em
  04/10/2026 no Claude Code 2.1.289: 9 pass, 0 fail; `claude plugin validate` sem aviso. Com o
  `register` ignorando a opção `dono`, o teste dela falha (8 pass, 1 fail).
- Diferenças em relação à pasta de origem, para servir a qualquer pessoa: os textos falavam do
  Fernando e do Mac, e agora falam de quem a opção `dono` disser e da máquina; o cabeçalho das
  respostas enviadas ao Claude passa a ser "Respostas às decisões"; o `plugin.json` ganha autor,
  repositório, licença e palavras-chave (o `validate` avisava a falta de autor); e as fixtures
  dos testes usam um workspace e um diretório de nome neutro no lugar dos de um projeto real.
