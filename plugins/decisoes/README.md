# decisoes

Um mod do Claude Code: um plugin de hooks em função (`hooks/register.tsx`), com faixa acima do
prompt e painel próprio. Ele junta, em cada sessão, as decisões que só o dono da sessão pode
tomar, deixa respondê-las por clique e leva às outras sessões abertas no cmux que também esperam
uma decisão.

## O que faz

- **Registra a decisão sem travar a sessão.** O agente ganha a ferramenta
  `mcp__decisoes__registrar_decisao` (pergunta, contexto, até 9 opções, a recomendada e se ele
  parou esperando) e uma instrução no prompt de sistema para usá-la em vez de só perguntar no
  texto: merge, deploy, escopo, prazo, aval, escolha entre caminhos de custo ou risco
  diferentes.
- **Pega também a pergunta deixada no texto.** Uma linha da resposta com 🔴, "aguardo seu aval",
  "preciso da sua decisão" ou "depende de você decidir" vira uma decisão de resposta livre, até
  três por turno.
- **Responde por clique.** A faixa acima do prompt mostra quantas decisões esperam e há quanto
  tempo; o botão "decidir" (ou `/decisoes`) abre o painel, uma decisão por vez, com as opções
  numeradas, resposta livre, "adiar" e "fechar". Quando a última pendente é respondida, as
  respostas vão juntas ao Claude como um turno.
- **Mostra as outras sessões.** Cada sessão grava um cadastro no armazenamento compartilhado dos
  plugins a cada 30 s; a faixa lista até quatro outras sessões com decisão pendente. Clicar leva
  à aba dela no cmux, ou, se a aba fechou, oferece retomar a sessão (`claude --resume`) numa aba
  nova do mesmo workspace. Fora do cmux, copia o comando de retomada.
- **Pousa a sessão.** "🛬 pousar" e "⚠ pouso de emergência" pedem ao agente que guarde o trabalho e
  registre onde parou antes de você fechar a máquina; a faixa avisa quando a resposta chega com
  `POUSO CONCLUÍDO`.

## Requisitos

- Um Claude Code com plugins de hooks em função (o formato `hooks/hooks.json` com `modules`).
  Validado e testado na 2.1.289.
- O cmux é opcional: sem ele, a faixa e o painel funcionam e a navegação para outra sessão cai
  no comando de retomada copiado.

## Instalação

```
/plugin marketplace add fernando-bertholdo/4-successful-AI-life
/plugin install decisoes@4-successful-ai-life
/reload-plugins
```

Os textos que o agente lê e os da faixa estão em português e falam do Fernando, o dono das
sessões para quem o mod foi escrito.

## Desenvolvimento

```
claude plugin validate plugins/decisoes
claude plugin test plugins/decisoes
```

Os tipos (`.claude-plugin/types/`) são escritos pelo próprio Claude Code quando o mod carrega e
não são versionados; depois disso, `tsc -p plugins/decisoes` confere o mod contra eles.
