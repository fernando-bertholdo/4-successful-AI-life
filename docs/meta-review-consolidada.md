# Meta-revisão consolidada — Documento A vs. Documento B

**Data:** 2026-08-13
**Árbitro:** revisor independente, sem lealdade a nenhum dos dois documentos.
**Método:** toda afirmação abaixo foi verificada nesta sessão contra os arquivos-fonte. Ratios de
contraste recalculados em Python (fórmula WCAG 2.x, sRGB relative luminance). Contagens de linha via
`wc -l`. Links de referência mapeados por script.

**Documentos julgados:**

- **A** — `docs/ui-excellence-vs-jakub-interfaces.md`
- **B** — `outputs/codex-review.md`

**Fontes primárias:**

- `plugins/ui-excellence/` (13 `SKILL.md`, 52 arquivos em `references/`, 21.521 linhas de markdown)
- `outputs/jakub-skills/` (clone de `jakubkrehel/skills`, 8 skills, 4.160 linhas)

---

## Placar

| | Procede | Procede parcialmente | Não procede | Ambos errados |
|---|---|---|---|---|
| Seção (a) — 15 objeções | 4 | 6 | 4 | 1 |
| Seção (c) — 11 objeções | 4 | 5 | 2 | 0 |

---

## 1. Veredito de cada objeção do Documento B

### Seção (a) — diagnósticos errados ou exagerados

---

**a1 — "As 12 contradições diretas não são uma lista de edição confiável."**
**Veredito: Procede.**

Auditei as 12 linhas da tabela §5.1 de A uma a uma. Resultado:

| # | Linha de A | Veredito verificado |
|---|---|---|
| 1 | Scale no press | **Real.** Quatro valores prescritivos distintos: `0.97` (`foundations/animation-motion/SKILL.md:143`), `0.96` (`foundations/visual-polish/SKILL.md:338,346`), `0.97` (`interaction/microinteractions/references/feedback-patterns.md:41`), `0.97` (`systems/refactoring/references/animation-microinteractions.md:147`), "2%" = 0.98 (`interaction/microinteractions/references/trigger-design.md:103`), `scale-95` = 0.95 (`systems/refactoring/references/advanced-patterns.md:161`, seção "### Active/Pressed") |
| 2 | Alvo 40 vs 44 | **Real, e A subcontou.** Existe um terceiro valor: `24x24` em `interaction/microinteractions/references/trigger-design.md:28` ("Desktop triggers should be at least 24x24 pixels") |
| 3 | Duração | **Parcial.** Ver a4 |
| 4 | `ease-in` | **Real.** `foundations/animation-motion/SKILL.md:83` "Never use `ease-in` for UI animations" vs. `foundations/visual-polish/SKILL.md:326` `animation: exitSubtle 400ms ease-in forwards` |
| 5 | Stagger | **Parcial.** Ver a5 |
| 6 | Line-height corpo | **Não é contradição.** Ver a6 |
| 7 | Escala de tipo | **Parcial.** Ver a7 |
| 8 | Breakpoints | **Parcial, e A errou os números.** Ver a8 |
| 9 | `#374151` | **Real.** Ver a9 |
| 10 | 3-4 vs 5-10 users | **Fraca / contextual.** `audit/heuristics/references/krug-principles.md:230` ("3-4 users catches most issues", teste de usabilidade heurístico) vs. `audit/cro/references/RESEARCH.md:93` ("DIY Testing (5-10 users is enough)", pesquisa de CRO). Métodos diferentes, skills diferentes. Não é instrução impossível |
| 11 | Prova social fabricada | **FALSA. A inventou esta contradição.** Ver §2.1 |
| 12 | Rótulo "Submit" | **Real, e mais grave do que A disse.** `trigger-design.md:26` e `:203` proíbem "Submit"; `case-studies.md:17,22,39` constrói o Caso 1 inteiro em torno de um botão "Submit" — **os dois arquivos são da mesma skill** (`interaction/microinteractions`) |

Placar da tabela §5.1 de A: **5 reais · 4 parciais · 1 fraca · 1 não-contradição · 1 fabricada.**
B está certo: a tabela não pode ser executada linha a linha sem triagem. Mas B também não identificou
a linha *fabricada* (#11), que é o erro mais grave da tabela.

---

**a2 — "Scale-on-press é conflito real, mas a evidência está inflada; `scale(0.95)` é entrada de modal."**
**Veredito: Não procede — B atacou uma citação que A não fez.**

B cita `advanced-patterns.md:338`. Verifiquei: `systems/refactoring/references/advanced-patterns.md:338`
é `transform: scale(0.95);` sob o cabeçalho `### Modal Transitions` (`:332`). B está certo *sobre essa
linha*. Mas A não citou `scale(0.95)` — A escreveu `active:scale-95`, que corresponde a
`systems/refactoring/references/advanced-patterns.md:161` (`- Slight scale down (\`scale-95\`)`) sob o
cabeçalho `### Active/Pressed` (`:159`). Esse é um valor de press legítimo. A linha de A permanece
válida com **quatro** valores distintos (0.95 / 0.96 / 0.97 / 0.98).

---

**a3 — "O diagnóstico de tamanho de alvo está meio certo."**
**Veredito: Procede parcialmente.**

Confirmado que "mobile accessibility standard" é falso: `foundations/visual-polish/SKILL.md:373`
("at least **40×40 pixels** (mobile accessibility standard)"). Não existe tal padrão.

B está certo que 24/40/44 são reconciliáveis por contexto — é exatamente o que Jakub faz em
`skills/better-accessibility/hit-areas.md:9-16`.

Mas B erra as linhas: cita `hit-areas.md:6,14`; `:6` é linha em branco, `:14` é a linha "Material
Design" da tabela. O texto operativo está em **`hit-areas.md:11`** (tabela: WCAG 2.5.8 AA = 24×24) e
**`hit-areas.md:16`** (a prosa que reconcilia os três). B também cita `web-standards/SKILL.md:784`
— correto (`- **Minimum 44×44px** touch target`).

Onde B se omite: dentro do `ui-excellence` os valores **não** estão separados por contexto — 40×40 é
prescrito para "All interactive" (`visual-polish/SKILL.md:445`, `:474`) e 44×44 também para "All
interactive" (`web-standards/SKILL.md:791`, `:1186`). São dois `min-height` incondicionais e mutuamente
exclusivos no mesmo plugin. Isso é conflito literal, não diferença de contexto.

---

**a4 — "A linha de duração mistura uma contradição interna real com classes de animação diferentes."**
**Veredito: Procede — e B encontrou algo que A não viu.**

Verificado: `foundations/animation-motion/SKILL.md:94` prescreve **200–500ms** para modais/drawers,
enquanto `:97` afirma "**Rule of thumb:** UI animations under 300ms" e o checklist `:496` repete
"**Duration under 300ms**". Contradição interna literal, no mesmo arquivo, a 3 linhas de distância.
**A não registrou isso.** As citações de B (`:94`, `:97`) estão corretas.

B também está certo que 800ms de entrada escalonada (`visual-polish/SKILL.md:442`; código em `:254`,
`:278`) e 500–800ms de transição de página (`web-standards/SKILL.md:400`) não são comparáveis a
micro-feedback. Porém o checklist de `animation-motion:496` não faz essa distinção — ele diz "UI
animations, not marketing videos", e uma transição de página é uma UI animation. A tensão cruzada
existe; ela é de escopo, não de valor.

---

**a5 — "A linha de stagger é majoritariamente não-contraditória."**
**Veredito: Procede parcialmente — B subestimou o conflito que ele mesmo apontou.**

Verificado:

- `foundations/animation-motion/SKILL.md:439-441` — incrementos de 50ms para itens de lista
- `foundations/visual-polish/SKILL.md:283` — "Sectional stagger: ~100ms delays between groups"
- `foundations/visual-polish/SKILL.md:284` — "Word-level stagger: ~80ms delays between individual items"
- `foundations/visual-polish/SKILL.md:294` — `delay: i * 0.1, // Stagger by 100ms` — **em botões, que são "individual items"**, contradizendo a linha `:284` do mesmo arquivo a 10 linhas de distância
- `foundations/visual-polish/SKILL.md:466` — checklist: "button delays ~100ms"
- `systems/refactoring/references/animation-microinteractions.md:423-424` — "0-50ms stagger: feels cohesive / **100ms+ stagger: feels slow, sequential**"

B descreveu o conflito estreito como "uma referência chama 100ms+ de lento enquanto `visual-polish`
recomenda ~100ms **entre seções**". Errado: `visual-polish` recomenda ~100ms **entre botões
individuais** (`:294`, `:466`) — exatamente a granularidade que `animation-microinteractions:424`
condena. Além disso `visual-polish` se contradiz internamente (80ms `:284` vs 100ms `:294`). A tinha
razão ao dizer "4 valores, dois deles no mesmo arquivo". As citações de B (`:440`, `:283`, `:423`)
estão corretas.

---

**a6 — "Os ranges de line-height são compatíveis, não contraditórios."**
**Veredito: Procede.**

`systems/typography/SKILL.md:211` e `:216` prescrevem 1.4–1.8 para corpo;
`systems/refactoring/SKILL.md:101` prescreve 1.5–1.75. 1.5–1.75 ⊂ 1.4–1.8. Citações de B corretas.
`systems/typography/references/css-implementation.md:356-359` define tokens 1.2/1.4/1.6/1.8, todos
dentro do range mais largo. **A errou ao chamar isso de contradição.** Sobra um problema real de
ownership (duas skills prescrevendo o mesmo parâmetro), que é outra coisa.

Nota: os ranges de heading divergem de verdade — 1.1–1.25 (`typography/SKILL.md:216`) vs 1.0–1.25
(`refactoring/SKILL.md:101`). Nenhum dos dois documentos notou. É trivial.

---

**a7 — "As duas escalas de tipo são exemplos concorrentes, não requisitos incompatíveis."**
**Veredito: Procede parcialmente.**

`systems/typography/references/css-implementation.md:347-354`: 0.75/0.875/1/1.125/1.25/1.5/2/2.5rem
(= 12/14/16/18/20/24/32/40px). `systems/refactoring/SKILL.md:100`: "Use a modular scale: 12, 14, 16,
20, 24, 30, 36px (1.25 ratio)". Divergem em 18/30/36 vs 32/40.

B suaviza: chama a segunda de "example 1.25-ratio product scale". O texto literal em `:100` é
imperativo — "**Use** a modular scale: …". A palavra "e.g." aparece em `:97` e se refere ao *ratio*,
não à escala. Ainda assim B tem razão no ponto central: um agente que recebe as duas escolhe uma; não
recebe uma instrução impossível. É problema de dono, não de contradição.

Erro de citação de B: cita `refactoring/SKILL.md:95`, que é a linha "**Core concept:**". A escala está
em **`:100`**.

---

**a8 — "O conflito de breakpoints está mal enunciado."**
**Veredito: Procede.**

`systems/typography/references/responsive-typography.md:244-249` lista **640, 768, 1024, 1440**.
A escreveu "640/1024/1440" — omitiu 768. B está certo, e as citações de B (`:242` = `### Key
Breakpoints`, `:247` = a linha 768px) estão corretas, assim como `advanced-patterns.md:277`.

A divergência real é só no topo: 1280/1536 (Tailwind, `advanced-patterns.md:279-284`) vs 1440
(`responsive-typography.md:249`). A caracterização de A na §4 ("1280/1536 vs 1440") está certa; a
linha da tabela §5.1 está errada.

---

**a9 — "Os cálculos de contraste estão de fato errados, mas 'defeito mais perigoso' é melodramático."**
**Veredito: Procede parcialmente. Ambos os documentos param antes da conclusão certa.**

Recalculei (WCAG 2.x, sRGB):

| Par | Publicado | Real (calculado) | Local | Threshold da linha | Passa? |
|---|---|---|---|---|---|
| `#333` / `#fff` | 12.6:1 | **12.6347:1** | `foundations/accessibility/SKILL.md:774` | 4.5 | sim |
| `#666` / `#fff` | 5.74:1 | **5.7418:1** | `:775` | 3 | sim |
| `#0066cc` / `#fff` | 8.59:1 | **5.5666:1** | `:776` | 3 | sim |
| `#555` / `#fff` | 9.26:1 | **7.4552:1** | `:777` | 7 | sim, por 6,5% de margem |
| `#374151` / `#fff` | 10.5:1 | **10.3074:1** | `systems/refactoring/SKILL.md:148` | — | sim |
| `#374151` / `#fff` | 9.1:1 | **10.3074:1** | `systems/refactoring/references/accessibility-depth.md:134` | — | sim |

Correção de citação: B cita `accessibility/SKILL.md:772,776`. `:772` é a linha de cabeçalho da tabela.
As duas linhas erradas são **`:776`** e **`:777`**.

Ambos erram na implicação:

- **A exagera.** Chamar isso de "o defeito mais perigoso do conjunto" é insustentável quando no mesmo
  plugin existem `foundations/accessibility/SKILL.md:723` (`expect(lastButton === document.activeElement);`
  — assertion sem matcher, passa sempre, valida um focus trap que não é testado) e o padrão de Dropdown
  em `:346-365` cujo teclado não funciona. Esses são copiáveis para produção; a tabela é consultiva.
- **B minimiza mal.** "Ambos ainda passam os thresholds atribuídos pela tabela, então os erros não
  revertem uma decisão de aprovar/reprovar" é verdade só dentro da linha. Fora dela é falso: um agente
  que lê "`#0066cc` on `#fff` = 8.59:1" conclui que `#0066cc` passa AAA para texto de corpo (7:1). O
  valor real é 5.5666 — **reprova AAA**. A tabela publica um número que licencia um uso que falha. Isso
  é reversão de decisão, só que a um hop de distância.

**Veredito correto:** erro factual de gravidade média-alta, corrigir hoje, mas não é o item mais
perigoso do conjunto — esse título pertence ao código de a11y quebrado.

---

**a10 — "A correção aritmética está certa, mas 'tempo perdido' segue sem base."**
**Veredito: Procede.**

`foundations/animation-motion/SKILL.md:524`: `// ❌ BAD — submitted 100x/day, animation compounds to
~3 min/day lost`, com um spinner de 300ms em `:526`. 100 × 300ms = 30s. Citação de B correta.
B também está certo que o exemplo apenas *inicia* um spinner (`showLoadingSpinner()`) — a animação não
adia a conclusão da tarefa em 300ms, então nem os 30s são "perdidos". O argumento inteiro do frequency
gate (`:46`, "every millisecond of animation compounds into frustration") apoia-se num exemplo que não
demonstra o que afirma.

---

**a11 — "As alegações de referências órfãs/inalcançáveis são literalmente falsas."**
**Veredito: Procede quanto ao fato. Mas nenhum dos dois formulou a crítica certa — e ambos erraram os números.**

Mapeei os 52 arquivos de `references/` por script. Resultado definitivo:

- **Zero arquivos sem nenhum link.** Todos os 52 aparecem na seção `## Reference Files` do respectivo
  `SKILL.md`. A palavra "órfão" e "inalcançável" são falsas. B está certo.
- **17 arquivos** (não 14, como diz A; não "todos linkados, nada a fazer", como sugere B) só são
  alcançados pelo índice final, nunca por um link inline no corpo:

| Skill | Arquivos só no índice | Linhas |
|---|---|---|
| `systems/refactoring` | `accessibility-depth.md`, `animation-microinteractions.md`, `data-visualization.md` | 1.448 |
| `audit/heuristics` | `audit-template.md`, `cultural-ux.md`, `wcag-checklist.md` | 933 |
| `behavior/copy` | `applications.md`, `case-studies.md`, `curse-of-knowledge.md` | 886 |
| `behavior/hooked` | `case-studies.md`, `neuroscience-foundations.md` | 621 |
| `audit/cro` | `COPYWRITING.md`, `funnel-analysis.md` | 557 |
| `behavior/retention` | `behavior-model.md`, `case-studies.md`, `product-applications.md` | 556 |
| `interaction/microinteractions` | `case-studies.md` | 371 |
| **Total** | **17 arquivos** | **5.372 linhas = 25,0% do plugin** |

A esqueceu os três de `behavior/copy`. A também errou o volume: disse "≈943 linhas inalcançáveis" para
os três de `refactoring`; o valor real é **1.448** (`accessibility-depth.md` 518 + `animation-microinteractions.md`
442 + `data-visualization.md` 488).

**A crítica correta**, que nenhum dos dois escreveu: o índice `## Reference Files` fica *depois* do
checklist de auto-revisão em todos os 8 casos (ex.: `systems/refactoring/SKILL.md:285`, depois da
tabela que termina em `:283`; `interaction/microinteractions/SKILL.md:222`, depois da tabela que termina
em `:220`). Um agente que lê o `SKILL.md` de cima para baixo e começa a trabalhar nunca chega lá no
momento em que precisaria. É exatamente o mecanismo que Jakub descreve em `AGENTS.md:19` — a razão pela
qual ele coloca a seção `Reporting` "where the agent lands before writing output". O problema não é
alcançabilidade topológica; é **posicionamento do ponteiro em relação ao momento de uso**. Jakub inclusive
proíbe o padrão: `AGENTS.md:17` — "No review checklists and **no trailing reference-file index**; the
Quick Reference is the only file listing."

Fato adicional que reforça A: em `systems/refactoring/SKILL.md`, **6 dos 7** links inline apontam para
o mesmo arquivo (`advanced-patterns.md` em `:58, :91, :124, :190, :222, :255`), e apenas `:157` aponta
para outro. Verificado, e A tinha razão.

---

**a12 — "A contagem de handoffs está errada e 'quebrado' precisa de qualificação."**
**Veredito: Procede.**

Contei nos 8 frontmatters adaptados do wondelai (linha `:3` de cada `SKILL.md`): **16 ocorrências**,
duas por descrição. B está certo; A escreveu "5" na §2, "cinco" na §5.3 e "8" no backlog #7 — três
números, todos errados, no mesmo documento.

Decomposição verificada:

- **7 ocorrências → 6 skills que não existem em lugar nenhum do plugin:** `top-design`
  (`systems/typography/SKILL.md:3`), `design-everyday-things` (`interaction/microinteractions/SKILL.md:3`),
  `one-page-marketing` (`audit/cro/SKILL.md:3`), `storybrand-messaging` e `contagious`
  (`behavior/copy/SKILL.md:3`), `contagious` de novo (`behavior/hooked/SKILL.md:3`), `drive-motivation`
  (`behavior/retention/SKILL.md:3`).
- **9 ocorrências → 6 aliases antigos de skills que existem:** `refactoring-ui` (×3), `ux-heuristics`
  (×2), `cro-methodology`, `web-typography`, `improve-retention`, `hooked-ux`.

E B está certo sobre o README: `plugins/ui-excellence/README.md:128-130` documenta a política — os 6
ausentes são "a pointer to the original wondelai/skills catalog", e a lista nominal em `:130` é
exatamente `top-design`, `contagious`, `drive-motivation`, `storybrand-messaging`, `one-page-marketing`,
`design-everyday-things`. **A ignorou esse parágrafo.** Só os 9 aliases são defeito puro.

Nuance que nem A nem B trataram: apesar de documentada, a política é operacionalmente inútil. A
`description` é o único texto sempre carregado de uma skill; gastar espaço nela apontando para skills
não instaláveis é custo de contexto sem retorno, e um agente não lê o README antes de rotear. A
política é defensável como atribuição e indefensável como roteamento.

---

**a13 — "O diagnóstico de escopo de `behavior/copy` está direcionalmente certo e numericamente indefensável."**
**Veredito: Procede parcialmente.**

Verificado com `cat SKILL.md references/*.md | wc -l`: **2.814 linhas**. A disse 2.823. B está certo.

Verificado: a tabela de A (linhas 224-230 de A) soma 45+15+15+8+7+10 = **100%** antes de adicionar os
3–5% de microcopy. Aritmeticamente impossível. B está certo. Acrescento: as categorias de A não são
reproduzíveis por nenhum critério declarado — não há como refazer a medição.

Mas B leu A mal em dois pontos:

- B: "It does contain … an error-message rule, so 'nothing' is false", citando `curse-of-knowledge.md:234`.
  A linha é: `- Error messages that use internal error codes instead of plain language` — um bullet de
  *sintoma* dentro de uma lista sobre documentação, sem regra e sem exemplo. E **A já tinha registrado
  exatamente isso**: "mensagens de erro (uma menção de passagem, zero exemplos)". B atacou uma ressalva
  que A fez.
- B está certo sobre CTA e onboarding: `references/applications.md:104` (`## Applying SUCCESs to
  Onboarding Flows`), `:142`, `:174` ("One action. Not 'Learn more, sign up, or reply.' Just one.").
  Mas é CTA de landing page, não rótulo de botão de interface.

Verificado a favor de A: **`empty state` tem zero ocorrências em todo o diretório `behavior/copy/`**.
A afirmação de A ("a expressão não aparece no arquivo") está certa.

Reformulação correta de B ("no systematic interface-microcopy coverage") é melhor que a de A. Adote-a.

---

**a14 — "Dois diagnósticos sobrevivem intactos (WCAG 2.1, `paths:` só no coordinator)."**
**Veredito: Procede.**

- `WCAG 2.2` tem **zero** ocorrências no plugin. `WCAG 2.1` aparece em 11 locais, incluindo
  `foundations/accessibility/SKILL.md:3`, `:6`, `:10`; `foundations/web-standards/SKILL.md:10`;
  `audit/heuristics/references/wcag-checklist.md:1`. `2.5.8`, `2.4.11`, `2.4.13`, `2.5.7`, `3.3.7`:
  zero ocorrências cada. Citações de B corretas.
- Varri o frontmatter dos 13 `SKILL.md`: `paths:` existe **só** em `_coordinator/SKILL.md:4`. Correto.

---

**a15 — "O inventário do cabeçalho está parcialmente errado."**
**Veredito: Ambos errados.** B acerta o ponto principal e depois publica um erro factual grosseiro.

Recontagem completa do cabeçalho de A:

| Alegação de A | Verificado | Veredito |
|---|---|---|
| 13 skills locais | `find . -name SKILL.md \| wc -l` = 13 | ✅ |
| 21.521 linhas | `wc -l` de todos os `.md` = 21.521 | ✅ exato |
| **47 arquivos de referência** | `find . -path "*/references/*" -name "*.md" \| wc -l` = **52** | ❌ **A errou; B está certo** |
| Versão `1.0.0-alpha.3` | `.claude-plugin/plugin.json:3` | ✅ |
| Jakub: 8 skills (6 domínios + 1 orquestrador + 1 review de diff) | ✅ | ✅ |
| Jakub: 4.160 linhas | `wc -l` = 4.160 | ✅ exato |
| Jakub: 27 arquivos de referência | 44 `.md` − 8 `SKILL.md` − 3 raiz − 6 `review-output.md` = 27 | ✅ exato |
| Jakub: versão `1.1.0` | `.claude-plugin/plugin.json:4` | ✅ |
| 5,2× mais conteúdo | 21521 / 4160 = 5,173 | ✅ |

**O anexo de A está 100% correto.** Verifiquei linha a linha:

| Skill | A diz | `wc -l` real | Refs (A) | Refs reais |
|---|---|---|---|---|
| `better-typography` | 136 | **136** | 6 + review-output | 6 + review-output |
| `better-colors` | 86 | **86** | 5 + review-output | 5 + review-output |
| `better-layout` | 79 | **79** | 2 + review-output | 2 + review-output |
| `better-writing` | 115 | **115** | 0 + review-output | 0 + review-output |
| `better-ui` | 108 | **108** | 6 + review-output | 6 + review-output |
| `better-accessibility` | 101 | **101** | 6 + review-output | 6 + review-output |
| `better-interface` | 187 | **187** | 0 | 0 |
| `interface-review` | 142 | **142** | 2 | 2 |

**B afirma: "it says `better-typography` has 136 lines while the current file has 108."** É falso.
`skills/better-typography/SKILL.md` tem exatamente **136** linhas. **108** é `skills/better-ui/SKILL.md`.
B confundiu dois arquivos e usou essa confusão para alegar que os números do Jakub em A "não são
reproduzíveis". São reproduzíveis, e são exatos — todos os 8. Este é o erro factual mais claro de B.

(A crítica de fundo de B — A cita `main` mutável sem SHA — é metodologicamente válida e vale adotar.)

---

### Seção (c) — priorização do backlog

---

**c1 — "'Adotar a governança dele, manter sua amplitude' não deve significar um audit monolítico."**
**Veredito: Procede.** Argumentação completa na §3.

Evidência verificada a favor de B: `_coordinator/SKILL.md:249` — `4. **Engagement** —
Behavior/retention/copy suggestions (**these are strategic, not defects**)`. A distinção já existe e é
correta. As três citações de B (`:230`, `:244`, `:249`) estão exatas — as únicas de B em todo o
documento que batem em cheio.

---

**c2 — "Adicionar um P0 novo antes de qualquer refatoração de conteúdo: provar ativação e empacotamento."**
**Veredito: Procede.**

`plugins/ui-excellence/README.md:118`: "**Note:** `paths:` auto-loading in plugin skills is aspirational
— empirical validation pending." `CHANGELOG.md:20-21` repete. Verificado que `paths:` existe só em
`_coordinator/SKILL.md:4`. Se o auto-load não dispara, o coordinator só roda quando invocado
manualmente — e nenhuma das 12 especialistas referencia o coordinator (grep exaustivo por
"coordinator" fora de `_coordinator/`: **zero resultados**). O grafo de invocação é, hoje, uma
suposição não testada. Item legítimo e barato.

---

**c3 — "P0 #1 e #2 devem ser rebaixados."**
**Veredito: Procede parcialmente.** Ver a9 e a10. #2 (aritmética) é claramente não-bloqueante. #1
(contraste) não é apenas "imprecisão de documentação": 8.59 publicado para um par que mede 5.5666
licencia um uso AAA que falha. Mantenha P0 mas com prioridade abaixo do código de a11y quebrado.

---

**c4 — "P0 deve reter #3, as partes confirmadamente danosas de #5, e #6."**
**Veredito: Procede.** Verifiquei cada citação de B:

- `visual-polish/SKILL.md:373` — "mobile accessibility standard" ✅
- `accessibility/SKILL.md:347` — `onKeyDown={handleMenuKeyDown}` no `<ul role="menu">` ✅
- `accessibility/SKILL.md:357` — `aria-selected={i === selectedIndex}` em `role="menuitem"` ✅ (não
  suportado; `menuitem` não aceita `aria-selected`)
- `accessibility/SKILL.md:723` — `expect(lastButton === document.activeElement);` ✅ sem matcher
- `typography/SKILL.md:246` — `h1, h2 { line-height: 1.1-1.25; }` ✅ CSS inválido
- `data-visualization.md:79` — `.bar-gap: 8px;` ✅ seletor usado como declaração, dentro de um bloco CSS

Todas as 6 citações de B corretas. Único acerto de precisão sistemática de B em todo o documento.

Nuance no Dropdown: A escreveu "as setas nunca disparam". Preciso: eventos de `keydown` dos `<button
role="menuitem">` **borbulham** até o `<ul>` e disparariam o handler. O defeito é que, ao abrir
(`:340`, `setIsOpen(!isOpen)`), o foco permanece no botão de trigger, que está **fora** do `<ul>` — e
nada dentro recebe foco programaticamente. Então as setas não funcionam no estado que importa. A
está certo na conclusão, impreciso no mecanismo.

---

**c5 — "Dividir o P0 #4; não é uma tarefa 'M'."**
**Veredito: Procede.**

Verificado, com as classificações de B corretas:

| Item | Local | Classe |
|---|---|---|
| `import { useQueryState } from "next-usp"` | `web-standards/SKILL.md:709` (a prosa em `:703` recomenda `nuqs`) | **Correção** — pacote inexistente |
| `priority` num `<img>` cru | `web-standards/SKILL.md:561-568` | **Correção** — prop só do `<Image>` do Next |
| `onKeyDown` Enter/Space num `<button>` nativo | `web-standards/SKILL.md:101-115` | **Correção** — dispara duas vezes |
| `navigator.language` em render + `<html lang>` retornado de um componente | `web-standards/SKILL.md:944`, `:962` | **Correção** — hydration mismatch, contradizendo a própria seção de Hydration Safety |
| `-webkit-overflow-scrolling: touch` | `web-standards/SKILL.md:802` | **Limpeza** — e o arquivo **já** diz "(deprecated but still supported)". A criticou como se não estivesse marcado |
| `clip: rect(0,0,0,0)` | `web-standards/SKILL.md:208` | **Não é defeito.** É a receita `.sr-only` padrão da indústria. Preferência estilística de A, não bug |
| UA sniffing `/iPhone\|iPad\|Android/` | `web-standards/SKILL.md:855` | **Limpeza** |
| Duas seções "Images" | `:168` (`### Images`) e `:549` (`## Images`) | **Limpeza** |

`web-standards/SKILL.md` tem 1.195 linhas com 8+ blocos de código React. Auditar é **G**, não **M**.
B correto.

---

**c6 — "Mover #21, #32 e #33 para P0/P1."**
**Veredito: Procede parcialmente.**

- **#21 (WCAG 2.2):** procede. Zero ocorrências de "WCAG 2.2"/2.5.8. O plugin *anuncia* conformidade
  ("ensure WCAG 2.1 compliance", `accessibility/SKILL.md:3`). Alegação de conformidade desatualizada é
  P1, não P2.
- **#32 (`forced-colors`):** procede. `forced-colors`, `prefers-contrast` e
  `prefers-reduced-transparency` têm **zero** ocorrências no plugin inteiro. E
  `visual-polish/SKILL.md:93-95` prescreve incondicionalmente "Replace flat `border` declarations with
  layered shadows" com a justificativa "Shadows adapt to any background" (`:113`) — falso sob
  forced-colors, onde `box-shadow` não é renderizado. Citação de B (`visual-polish/SKILL.md:93`) correta.
- **#33 (reduced motion como substituição):** procede, e o problema é pior do que ambos disseram. Há
  **4** snippets distintos, não 3, e nenhum faz substituição:
  `animation-motion/SKILL.md:403` (`0.01ms !important`), `animation-motion/SKILL.md:570`
  (`animation: none`), `web-standards/SKILL.md:376` (`animation: none !important; transition: none
  !important`), `animation-microinteractions.md:363` (`0.01ms`). Os dois que usam `none` são
  tecnicamente piores: matam os eventos `animationend`/`transitionend` e travam JS que os aguarda —
  exatamente o que Jakub explica em `better-accessibility/motion-and-zoom.md:39`. O modelo de
  substituição de Jakub está em `motion-and-zoom.md:43-49` (tabela Disable / Replace / Keep).

Onde B erra a contagem: A afirmou "aparece em 9 outros lugares". O real é **7 arquivos / 20
ocorrências**. B não conferiu.

---

**c7 — "Mover #27 e #18 à frente da maior parte do trabalho de formato; #11 é 'G', não 'M'."**
**Veredito: Procede parcialmente.**

A dependência que B aponta é real e verificável: `better-interface/SKILL.md:53` diz que, quando uma
skill de domínio é carregada pelo orquestrador, ela **ignora** sua própria seção `Reporting` e o
`review-output.md`, e usa o formato consolidado do orquestrador. Ou seja: sem o orquestrador definido
primeiro, os 13 `review-output.md` não têm a quem deferir. B correto na ordem.

B erra em #11: A escreveu explicitamente "**Começar pelas 4 de `foundations`**". Não são 13 arquivos
na primeira leva. Com o modelo do Jakub — 6 arquivos `review-output.md` compartilham o mesmo texto
verbatim em `:9` ("Never use separate 'Before:' / 'After:' lines") — o custo marginal por arquivo é
baixo. **M** é defensável para a primeira leva.

Erro de citação de B: cita `jakub AGENTS.md:16` (linha em branco). O conteúdo relevante está em
`AGENTS.md:17-19`.

---

**c8 — "#7 pertence ao P1 e deve ser reescrito como 16 falhas de resolução local em 8 descrições."**
**Veredito: Procede.** Ver a12. A reescrita de B é a correta e está incorporada no backlog final
(item 9).

---

**c9 — "Não executar #10, #13, #16 ou #19 como escritos."**
**Veredito: Procede parcialmente — 3 de 4.**

- **#10 (unificar severidade):** B procede. Mas nenhum dos dois contou direito. Ver §2.3: A alegou "4
  esquemas de severidade mutuamente inconsistentes" e dois deles são **o mesmo esquema**.
- **#13 (read-only por padrão):** procede parcialmente. B diz que "reviewing or creating" é escopo de
  descoberta, não permissão de mutação. Para `cro` isso está certo — a frase está em
  `audit/cro/SKILL.md:22`, dentro do bloco "Goal: 10/10", governando *quando aplicar a nota*, não
  autorizando edição. **B citou a linha errada** (`cro/SKILL.md:3`, que é a description). Mas para
  `heuristics` B está errado: `audit/heuristics/SKILL.md:3` literalmente abre com "**Evaluate and
  improve** interface usability using heuristic analysis" — isso está na `description`, o texto sempre
  carregado, e é uma declaração de escopo que inclui mutação. A regra read-only deve ser adicionada;
  o texto de `heuristics:3` deve mudar.
- **#16 (especialistas referenciarem o coordinator):** B procede. Jakub resolve isso com hierarquia,
  não com reciprocidade: `AGENTS.md:26` — "A user-invoked skill may invoke model-invoked skills, but it
  can never reach another user-invoked skill." A dependência é unidirecional por design
  (`AGENTS.md:52`: "The dependency runs one way"). A proposta de A ("e vice-versa") criaria o ciclo que
  Jakub proíbe explicitamente.
- **#19 (deletar `accessibility-depth.md` e a seção a11y de `krug-principles.md`):** B procede.
  `accessibility-depth.md` tem 518 linhas e contém material que não existe em nenhum outro lugar do
  plugin — é o único arquivo com `aria-pressed` (`:355`) e a única fonte do caveat honesto sobre
  cobertura de ferramentas automatizadas. Deletar antes de análise de conteúdo único é destrutivo.

---

**c10 — "#17 deve ser substituído, não executado."**
**Veredito: Procede parcialmente.**

B está certo que "linkar os órfãos" é a ação errada (eles já estão linkados). Mas a proposta de B —
"remover índices finais redundantes só depois de confirmar que toda referência continua alcançável" —
está incompleta. A ação correta, derivada de `AGENTS.md:17-18`: mover cada arquivo para uma **tabela
Quick Reference no topo** (o padrão que Jakub usa e que resolve o problema de posicionamento), e só
então remover o índice final. Números corretos: **17** arquivos, **5.372 linhas**, não 14.

---

**c11 — "#40 não vale como regra geral."**
**Veredito: Não procede. B contradiz a fonte que cita.**

B: "asking the user … is justified only when preserving a sub-16px design is explicitly required",
citando `details-and-accessibility.md:48,56`.

Texto real em `skills/better-typography/details-and-accessibility.md:59`: "Two fixes work, and they
differ in what they do to the design rather than in correctness. **Ask which one the user wants before
changing an input; do not pick for them.**" Incondicional. Sem exceção.

As citações de B estão erradas: `:48` é sobre a Custom Highlight API; `:56` é linha em branco. A seção
começa em `:55` e a regra está em `:59`. **A reportou Jakub corretamente; B não.** Mantenha o item.

---

## 2. O que os DOIS deixaram passar

### 2.1 A tabela §5.1 de A contém uma contradição inventada — e B não a achou

**Linha "Prova social fabricada | Endossada como trigger de Social Proof vs. nomeada como dark pattern
| `PERSUASION.md` vs `dark-patterns.md`".** É falsa.

- `audit/cro/references/PERSUASION.md:71` diz literalmente: "**Warning**: Fake scarcity destroys trust.
  Only use real limitations."
- `audit/cro/references/PERSUASION.md:74` lista "Join 50,000+ marketers" como Social Proof.
- `audit/heuristics/references/dark-patterns.md:328` lista "**Social proof (join 100k subscribers)**"
  como a **alternativa ética** à urgência falsa.

Os dois arquivos usam o *mesmo* padrão com a *mesma* postura. `dark-patterns.md:223` condena "15 people
viewing this" **(fabricated)**; `PERSUASION.md` nunca endossa fabricar nada. B, que dedicou sua objeção
mais forte a dizer que a tabela §5.1 não é confiável, não identificou a única linha fabricada dela.

### 2.2 Buraco de licenciamento e atribuição — nenhum dos dois tocou no assunto

`plugins/ui-excellence/README.md:139` classifica o grupo `foundations/` (4 skills) como "**Original
content** authored by Fernando Bertholdo". `LICENSE` reproduz um único aviso de copyright de terceiro:
o do wondelai.

Mas `_coordinator/SKILL.md:277-281` credita, para `foundations/`: **Emil Kowalski**, **Jakub Krehel**,
**Vercel** e **WCAG 2.1**. E `README.md:31` descreve `visual-polish` como "**Jakub Krehel's
principles**".

O grau de derivação de `visual-polish` a partir do material do Jakub é verificável e alto:

| Regra | `ui-excellence` | `jakubkrehel/skills` |
|---|---|---|
| Raio concêntrico | `visual-polish/SKILL.md:68` `outer_radius = inner_radius + padding` | `better-ui/surfaces.md:10` `outerRadius = innerRadius + padding` |
| Outline de imagem 1px opacidade baixa | `visual-polish/SKILL.md:122` | `better-ui/SKILL.md:60`, `better-ui/surfaces.md:193` |
| `text-wrap: balance` em headings | `visual-polish/SKILL.md:41,56` | `better-typography/SKILL.md:68`, `css-cheat-sheet.md:40` |
| `-webkit-font-smoothing: antialiased` na raiz | `visual-polish/SKILL.md:144-149` | `better-typography/css-cheat-sheet.md:15`, `details-and-accessibility.md:113-114` |
| `font-variant-numeric: tabular-nums` | `visual-polish/SKILL.md:161` | `better-typography/css-cheat-sheet.md:22` |
| `will-change` com parcimônia | `visual-polish/SKILL.md:414-423` | `better-ui/performance.md:45-56` |

O repo do Jakub é MIT © 2026 Jakub Krehel (`outputs/jakub-skills/LICENSE:3`). A licença MIT exige que
o aviso de copyright seja reproduzido em "all copies or substantial portions of the Software".
`plugins/ui-excellence/LICENSE` não o reproduz — reproduz só o do wondelai. Simultaneamente, o README
declara esse mesmo conteúdo como original.

**Isto é o risco mais concreto do plugin e nenhum dos dois documentos o menciona.** É P0, mais urgente
que qualquer ratio de contraste. Ação: reproduzir os avisos MIT de Jakub Krehel e de Vercel (Web
Interface Guidelines) no `LICENSE`, corrigir `README.md:139` para não chamar `foundations/` de conteúdo
original, e adicionar `foundations/` à tabela de proveniência.

### 2.3 A contagem de "4 esquemas de severidade" de A está errada — e B repetiu a premissa

A afirma (§5.2) quatro esquemas mutuamente inconsistentes. Verificado:

| Alegação de A | Realidade |
|---|---|
| 1. `heuristics/SKILL.md` — 0 a 4 | ✅ `audit/heuristics/SKILL.md:197-203`, escala 0–4 com Not a problem / Cosmetic / Minor / Major / Catastrophic |
| 2. `audit-template.md` — "Low/Medium/High/Critical, colunas invertidas" | ❌ **É a mesma escala.** `references/audit-template.md:19-25` usa 0–4 com os **mesmos rótulos**. Low/Medium/High/Critical é a coluna **Priority**, não a severidade. A única diferença real é a ordem das colunas do cabeçalho e o vocabulário de prioridade (`Ignore/Fix if time/Schedule fix/Fix soon/Fix immediately` vs `—/Low/Medium/High/Critical`) |
| 3. `cro` — ICE 1–10 com duas fórmulas | ✅ `references/testing-methodology.md:202` `(Impact + Confidence + Ease) / 3` e `:207` `(Impact × 2 + Confidence × 1.5 + Ease × 1) / 4.5`. Mas ICE é **priorização de experimento**, não severidade de defeito — categoria diferente |
| 4. `_coordinator` — Must/Should/Polish/Engagement | ✅ `_coordinator/SKILL.md:246-249` |

**O que A não contou:** existe um **quinto** vocabulário, e é o mais disseminado. A frase "**Goal:
10/10.** … rate 0-10 …" aparece **verbatim em 8 skills**, não nas 5 que A alega:
`audit/heuristics/SKILL.md:22`, `audit/cro/SKILL.md:22`, `systems/refactoring/SKILL.md:22`,
`systems/typography/SKILL.md:24`, `interaction/microinteractions/SKILL.md:20`,
`behavior/hooked/SKILL.md:28`, `behavior/retention/SKILL.md:37`, `behavior/copy/SKILL.md:22`.
Ou seja: **todas as 8 skills adaptadas do wondelai**.

**Contagem correta:** 3 vocabulários de saída (0–4 de severidade heurística; 0–10 de qualidade sem
rubrica em 8 skills; Must/Should/Polish/Engagement no coordinator) + 1 escala de priorização (ICE,
com duas fórmulas concorrentes). Não "4 esquemas de severidade".

### 2.4 A atribui ao `_coordinator` um defeito que ele não tem

Nas tabelas de A da §2 e da §4, a linha "Veredito" coloca no `_coordinator` "Score 0–10 sem rubrica".
Falso. O `_coordinator` **não tem** score 0–10 — grep exaustivo confirma. Ele tem
Must Fix / Should Fix / Polish / Engagement (`_coordinator/SKILL.md:246-249`). O score 0–10 está nas 8
especialistas do wondelai. A comparação está apontada para o arquivo errado.

### 2.5 Erros de contagem de A sobre o `_coordinator`

A: "13 combinações de multi-routing". A tabela em `_coordinator/SKILL.md:183-200` tem **16 linhas** — e
o próprio `README.md:114` e `CHANGELOG.md:15` já dizem "16-entry Multi-Routing table". A árvore de
decisão (`:70-106`) tem **12 padrões**, também documentado no README. A errou um número que já estava
correto na documentação do próprio repo.

### 2.6 A publica uma citação fabricada do Jakub

Verifiquei todas as 19 citações verbatim de A do repo do Jakub. **18 são exatas.** Amostra:
`AGENTS.md:18` (regra de ouro princípio/reference), `AGENTS.md:19` (dead weight in context; Reporting
section), `better-interface/SKILL.md:84` (cap/blocker), `:98` (Not verified), `:102` (read-only),
`:38` (leverage, not permission), `better-ui/SKILL.md:10` (10% speed), `:60` (dirt on the image edge),
`:88` (only feedback channel), `better-writing/SKILL.md:23` e `:38`, `better-typography/SKILL.md:40`
(not a diagnostic), `choosing-fonts.md:30` (paid or proprietary), `better-accessibility/SKILL.md:66`
(opacity crossfades), `better-layout/spacing-and-adaptivity.md:159` (modal action row),
`interface-review/SKILL.md:35` (twelve-commit branch), `review-output.md:9` × 6 (Before:/After:).

**A exceção**, na §4 de A sobre hit area, apresentada entre aspas e em itálico:

> A escreveu: *"WCAG 2.5.8's Level AA baseline is a 24×24 CSS-pixel target or one of its defined
> spacing, equivalent-control, inline, user-agent, or essential exceptions. For easier activation, aim
> for 44×44px in touch contexts and 40×40px in desktop interfaces when density permits."*

Texto real, `better-accessibility/hit-areas.md:16`:

> "WCAG 2.5.8 Level AA requires a 24×24 CSS-pixel target or one of its defined exceptions. Treat 44px
> as a recommended touch target for primary controls and 40px as a useful desktop target when the
> product's density permits. Smaller controls are not automatically failures: check the spacing,
> equivalent-control, inline, user-agent, and essential exceptions before reporting one."

A substância está certa; a citação é uma recombinação apresentada como verbatim. Num documento cuja
taxa de fidelidade é 18/19, isso é um deslize — mas é o tipo de deslize que o próprio A propõe
eliminar (backlog #12, exigência de evidência).

### 2.7 Regras técnicas do Jakub que nenhum dos dois capturou

B listou algumas em (b) mas **errou todas as linhas** (correções abaixo). Estas nenhum dos dois listou:

| Regra | Local verificado |
|---|---|
| Sob reduced motion, **carrosséis iniciam pausados**; animações devem ser interrompíveis e dirigidas por input | `better-accessibility/motion-and-zoom.md:51` |
| `0.01ms` em vez de `none` para que `animationend`/`transitionend` ainda disparem e o JS que os aguarda não trave | `better-accessibility/motion-and-zoom.md:39` — **contraria diretamente `web-standards/SKILL.md:378` e `animation-motion/SKILL.md:571`** |
| Nunca perder input digitado num re-render; **hydration deve preservar foco e valor** | `better-accessibility/forms.md:84` (B citou `:74`) |
| Navegação SPA: atualizar `document.title`, mover foco para o `<h1>` da nova view com `tabindex="-1"` ou para `<main>`, restaurar scroll no back/forward | `better-accessibility/focus-and-keyboard.md:129-131` (B citou `:112`) |
| Cor sobre superfície translúcida muda com o que rola atrás: testar sobre o conteúdo mais claro **e** o mais escuro possível | `better-colors/color-usage.md:94` (B citou `:79`) |
| Ícone na grade de pixel do tamanho de render: 16px desenhado numa grade de 24px com escala fracionária renderiza mole; usar as grades nativas (16/20/24) | `better-ui/icons.md:84` (B citou `:70`) |
| Em RTL, virar **só** ícones cujo significado depende da direção de leitura; ícones compostos analisados por partes (o badge pode não virar) | `better-ui/icons.md:89-91`, `:110` (B citou `:77`) |
| Toda cor de fg/bg deve ser rechecada nas duas aparências — as paletas não são espelhos | `better-colors/color-usage.md:93` |
| APCA é polarity-aware: pares espelhados não pontuam igual | `better-colors/accessibility-contrast.md:61` |
| Detecção de rename com janela de similaridade ajustável para arquivos movidos e editados na mesma mudança | `interface-review/scope-resolution.md:111-113` |
| Clone shallow: `--deepen=50`, depois `--deepen=200`, depois reportar escopo irresolvível — deepen escreve só em `.git`, logo é permitido | `interface-review/scope-resolution.md:81` |
| PR de fork: buscar a head num ref remoto isolado e ler com `git show refs/remotes/pr/<n>:path`; **não** abrir a cópia da working tree, que num fork é outro arquivo | `interface-review/scope-resolution.md:54`, `:63` |
| Alvo `working` inclui untracked via `git ls-files --others --exclude-standard` | `interface-review/scope-resolution.md:39` |
| Toda escrita em `.git` (fetch, deepen, set-head, worktree) deve ser listada na seção Verification, para que a alegação de read-only seja auditável | `interface-review/SKILL.md:142` |

**Escape conditions** (B mencionou; verifico e confirmo, corrigindo linhas):

- Raio concêntrico deixa de ser estrito acima de `24px` de padding — `better-ui/surfaces.md:13` ✅ (B correto)
- Densidade usável estabelecida vence números de espaçamento importados — `better-layout/SKILL.md:12` (B citou `:11`)
- Review de tipografia nunca justifica introduzir uma face paga — `better-typography/choosing-fonts.md:30` (B citou `:24`)

### 2.8 Coisas do `ui-excellence` que nenhum dos dois notou

- **`aria-pressed` existe** — `systems/refactoring/references/accessibility-depth.md:355`. A afirmou
  "sem `aria-pressed`" no plugin. Uma ocorrência, no arquivo que o item #19 de A quer deletar.
- **`inert` existe** — `foundations/web-standards/SKILL.md:819`, num contexto de drag-and-drop. A
  listou `inert` como ausente do plugin. Está ausente da skill de a11y e do padrão de Modal — o que é
  o ponto real —, mas não do plugin.
- **`:focus-visible` está em 4 arquivos**, não só em `web-standards`: `foundations/web-standards/SKILL.md`,
  `audit/heuristics/references/wcag-checklist.md`, `systems/refactoring/references/advanced-patterns.md`,
  `systems/refactoring/references/accessibility-depth.md`. A afirmou "só em `web-standards`". A parte
  verdadeira é que está ausente de `foundations/accessibility/SKILL.md`.
- **`foundations/accessibility/SKILL.md` tem 630 de 986 linhas dentro de blocos de código** (409 `jsx`,
  125 `html`, 65 `javascript`, 31 `css`) = 64% do arquivo. A estimou "~450 são componentes React";
  o número real de linhas React é 474 (jsx+javascript). A está aproximadamente certo, mas a estatística
  relevante é a outra: **quase dois terços da skill principal de a11y é código, e é o código que contém
  os quatro defeitos de `c4`**.
- **Contradição fora do inventário de A:** `foundations/animation-motion/SKILL.md:495` (checklist:
  "Not using CSS `ease`, `ease-in`, or `ease-out` defaults") proíbe exatamente as keywords que a tabela
  do mesmo arquivo em `:68-71` prescreve por cenário (ease-out / ease-in-out / ease / linear). A mencionou
  isso em prosa (linha 347 de A) mas não como item de backlog. Deveria ser.
- **`plugins/ui-excellence/README.md:13`** afirma que cada skill "is framework-agnostic and focuses on
  decisions, trade-offs, and concrete checklists **rather than boilerplate code**". Com 630 linhas de
  código em `accessibility/SKILL.md` e 8+ blocos React em `web-standards/SKILL.md`, a frase é falsa em
  dois eixos. A identificou (backlog #23); B não comentou. Confirmo A.

### 2.9 Onde A e B concordam e ambos estão errados

1. **Que a §5.1 de A precisa de "triagem".** Ambos tratam a tabela como uma lista de itens verdadeiros
   mal classificados. Uma das 12 linhas (prova social) é **falsa**, não mal classificada. Uma triagem
   que só reclassifica manteria uma alegação inventada no backlog. Ver §2.1.
2. **Que o `_coordinator` não tem tratamento de conflito.** Ambos aceitam isso. É verdade que não há
   arbitragem *de valor*, mas o `_coordinator` **tem** uma ordem de precedência de 9 camadas
   (`:232-240`) que já implementa a regra de Jakub "a11y → layout → … so foundational failures are not
   hidden by polish" (`better-interface/SKILL.md`, princípio de ordem). A rotula isso com um ✓ mas depois
   escreve "O que falta é tudo que vem depois do roteamento" — o que subestima o ativo existente. B nem
   menciona. A camada 9 (`:240`, "Behavior … engagement layer last") combinada com `:249`
   ("these are strategic, not defects") já é, na prática, o modelo de dois pacotes que B propõe. **Ele
   já existe; o que falta é torná-lo explícito e vinculante.**
3. **Que "13 skills" é uma contagem estável.** Ambos repetem. `AGENTS.md:62` do Jakub: "Prefer counts
   and lists that cannot go stale. Say 'every skill in this repository' rather than a number the next
   skill invalidates." A contagem "13 skills" está hard-coded em 5 lugares:
   `.claude-plugin/plugin.json:4`, `.claude-plugin/marketplace.json:14`, `README.md:3`, `README.md:22`,
   `README.md:122`. Adicionar `foundations/color` (item de A) quebra os 5 simultaneamente. Nenhum dos
   dois propôs remover as contagens.

---

## 3. Julgamento estratégico

### 3.1 Um audit monolítico ou dois pacotes?

**B está mais certo que A, mas nenhum dos dois enxerga a partição real. Proponho três contratos de
saída, não dois pacotes.**

Evidência do que existe hoje:

- `_coordinator/SKILL.md:246-249` já produz quatro grupos, e o quarto é explicitamente marcado
  "**these are strategic, not defects**".
- `_coordinator/SKILL.md:240` já coloca behavior como camada 9 de 9.
- `audit/heuristics/SKILL.md:197-203` produz uma **lista de defeitos** com escala 0–4 e fatores
  Frequency/Impact/Persistence (`:207-211`). É a mesma categoria de saída que uma finding de
  acessibilidade — um problema observado numa interface existente.
- `audit/cro/SKILL.md:174` e `references/testing-methodology.md:165-208` produzem uma coisa
  estruturalmente diferente: um **backlog de experimentos priorizado por ICE**, com hipótese, e cujo
  resultado só é conhecido *após* rodar o teste. `cro/SKILL.md:242` até proíbe tratar best practice
  como regra: "Treat best practices as hypotheses to test, not rules to follow."
- `behavior/hooked`, `behavior/retention`, `behavior/copy` produzem **recomendações estratégicas** —
  desenho de loop, milestone de ativação, mensagem. Não são defeitos nem experimentos.

A proposta de A (uma severidade compartilhada para tudo) **destrói informação**: força uma hipótese de
CRO não testada e um defeito de teclado confirmado no mesmo eixo. Além disso, A já tem a evidência
contra si própria no repo e não a leu — `_coordinator:249` diz o oposto.

A proposta de B (dois pacotes) melhora, mas coloca `cro` no lado errado da linha. `cro` não produz
"recomendações estratégicas": produz um backlog priorizado com uma métrica própria (ICE), cuja
priorização não é comparável nem a severidade nem a estratégia.

**Arquitetura proposta — três contratos, um roteador:**

| Contrato | Skills | Escala | Saída | Veredito |
|---|---|---|---|---|
| **Defeito** | `foundations/*` (4), `systems/*` (2), `interaction/microinteractions`, `audit/heuristics` | HIGH / MEDIUM / LOW + escalation triggers (modelo `better-interface/SKILL.md:66-84`) | Tabela: Severity · Location `path:line` · Before · After · Why | **Block / Needs changes / Approve** |
| **Experimento** | `audit/cro` | ICE 1–10, **uma** fórmula (aposentar a segunda em `testing-methodology.md:207`) | Hipótese · ICE · métrica primária · tamanho de amostra | Nenhum. Um experimento não bloqueia merge |
| **Recomendação** | `behavior/hooked`, `behavior/retention`, `behavior/copy` | Nenhuma escala numérica. Aposentar "Goal: 10/10" | Observação · mecanismo proposto · risco ético · como medir | Nenhum |

Três regras de ligação, que é onde está o valor:

1. **A escala HIGH/MEDIUM/LOW é a única que produz veredito de merge.** ICE e as recomendações nunca
   entram no veredito. Isso preserva `_coordinator:249` e o torna vinculante em vez de decorativo.
2. **A severidade 0–4 de `heuristics` mapeia para a escala compartilhada** (4→HIGH, 3→HIGH, 2→MEDIUM,
   1→LOW, 0→descartar) em vez de ser aposentada. Preserva o instrumento de domínio (que B defende com
   razão) e ainda entrega uma saída única. `audit-template.md:19-25` já usa a mesma escala 0–4, então
   os dois convergem sem edição de conteúdo.
3. **Os escalation triggers do Jakub (`better-interface/SKILL.md:73-83`, 8 gatilhos) atravessam os três
   contratos.** Se `behavior/hooked` propõe um loop que esconde a ação de saída, isso vira HIGH no
   contrato de defeito, não uma recomendação. É o mecanismo que impede que um pacote de conversão
   lave um dark pattern — e o plugin já tem o vocabulário para isso em
   `audit/heuristics/references/dark-patterns.md` e `behavior/hooked/references/ethical-boundaries.md`.

### 3.2 A tese central de A se sustenta?

**"O problema não é cobertura, é governança" — sustenta-se, mas por razões diferentes das que A deu, e
com uma exceção que A subestimou.**

*Sustenta-se porque:*

- Ownership: 8 dos 12 especialistas carregam a mesma frase "Goal: 10/10" verbatim; nenhum dos 12
  referencia o coordinator; 9 aliases de skill inválidos nas descrições sempre carregadas; 5 conflitos
  de valor literais confirmados (não 12); 3 vocabulários de saída sem arbitragem.
- Alcançabilidade: 25% do plugin (5.372 linhas, 17 arquivos) só é alcançável por um índice posicionado
  depois do checklist de auto-revisão — precisamente o anti-padrão que `AGENTS.md:17` proíbe.
- Confiabilidade: 6 defeitos de código copiáveis para produção confirmados, 2 ratios errados, 1 padrão
  inexistente ("mobile accessibility standard"), 1 dependência inexistente (`next-usp`), 2 blocos de
  CSS inválido.
- Custo de contexto: `web-standards/SKILL.md` = 1.195 linhas; `accessibility/SKILL.md` = 985, das quais
  630 são código. Nenhuma progressive disclosure. Isso é falha de governança, não de conteúdo.

*Não se sustenta integralmente porque:*

A trata cobertura como resolvida e ela não está — em três domínios a lacuna é **estrutural**, não de
governança, e nenhuma refatoração de formato a fecha:

- **Cor:** `oklch`, `color-mix`, `prefers-contrast`, `prefers-reduced-transparency`, `forced-colors`,
  `APCA` — **zero ocorrências cada** no plugin inteiro. Não há dono, não há conteúdo, e o conteúdo
  espalhado (heurística HSL em `refactoring §4`) é de outra época.
- **Layout:** sem sistema de grid, sem escala de z-index (2 ocorrências isoladas: `accessibility:153`,
  `case-studies.md:354`), container queries em um único arquivo
  (`responsive-typography.md:251-264`).
- **UX writing de interface:** `sentence case` = zero ocorrências; `empty state` = zero ocorrências em
  `behavior/copy/`.

E o `README.md:13` ("framework-agnostic … rather than boilerplate code") é falso — isso é uma alegação
de cobertura errada, não de governança.

**Formulação corrigida:** *o problema dominante é governança, mas há três lacunas de cobertura
verdadeiras (cor, layout, UX writing) e um problema de licenciamento que precede ambos.* A ordem certa
é: licença → defeitos copiáveis → governança → cobertura.

---

## 4. Backlog final consolidado

Esforço: **P** < 1h · **M** algumas horas · **G** dias.
Ordenado por dependência real. Itens marcados 🚫 **não devem ser executados**.

| # | Ação | Skill/arquivo | Prio | Esf. | Origem | Justificativa |
|---|---|---|---|---|---|---|
| 1 | Reproduzir os avisos MIT de Jakub Krehel e de Vercel no `LICENSE`; corrigir `README.md:139` para não classificar `foundations/` como "Original content"; adicionar `foundations/` à tabela de proveniência | `plugins/ui-excellence/LICENSE`, `README.md:139` | **P0** | P | **novo** | `README.md:31` e `_coordinator:277-281` creditam Jakub/Kowalski/Vercel; o `LICENSE` só reproduz o aviso do wondelai — exigência MIT não cumprida |
| 2 | Consertar os 4 defeitos de código copiáveis de a11y: foco inicial no Dropdown, remover `aria-selected` de `role="menuitem"`, dar matcher ao `expect()`, remover a restauração dupla de foco no Modal e ampliar o seletor de focáveis | `foundations/accessibility/SKILL.md:346-365`, `:723`, `:383-428` | **P0** | M | A+B | Copiáveis para produção; `:723` passa sempre em silêncio |
| 3 | Remover a alegação "mobile accessibility standard" e ancorar em WCAG 2.5.8 (24×24 AA / 44 touch / 40 desktop), reconciliando com `web-standards:784` e `trigger-design.md:28` | `foundations/visual-polish/SKILL.md:373`, `:445`, `:474` | **P0** | P | A+B (**reescrito**) | O padrão não existe; e há **três** valores no plugin (24/40/44), não dois |
| 4 | Corrigir CSS inválido: `line-height: 1.1-1.25` → valor único; `.bar-gap: 8px` / `.bar-width: 32px` → custom properties ou remoção | `systems/typography/SKILL.md:246`, `systems/refactoring/references/data-visualization.md:79-80` | **P0** | P | A+B | Declaração morta se copiada |
| 5 | Corrigir os 4 erros de correção em `web-standards`: `next-usp`→`nuqs`, remover `priority` do `<img>` cru, remover `onKeyDown` do `<button>` nativo, tirar `navigator.language` do render e o `<html>` de dentro do componente | `foundations/web-standards/SKILL.md:709`, `:561-568`, `:101-115`, `:944-964` | **P0** | M | A+B (**dividido**) | Só as correções. Limpeza vai no item 22 |
| 6 | Corrigir os dois ratios errados da tabela Quick Check: `#0066cc/#fff` = **5.57:1**, `#555/#fff` = **7.46:1** | `foundations/accessibility/SKILL.md:776`, `:777` | **P0** | P | A+B (**recalibrado**) | Ambos ainda passam o threshold da própria linha, mas 8.59 licencia um uso AAA que falha (real 5.57 < 7) |
| 7 | Corrigir `10.5:1` e `9.1:1` para **10.31:1** | `systems/refactoring/SKILL.md:148`, `references/accessibility-depth.md:134` | **P0** | P | A+B | Dois valores errados para o mesmo par, dentro da mesma skill |
| 8 | Corrigir a aritmética: 100 × 300ms = **30s**, não 3 min — e reescrever o exemplo, que só inicia um spinner e não demonstra atraso na tarefa | `foundations/animation-motion/SKILL.md:524-527` | P1 | P | A+B | B tem razão: nem os 30s são "perdidos" com esse código |
| 9 | Substituir os **9 aliases inválidos** pelos nomes canônicos nas descrições; decidir e aplicar uma política única para os **7 ponteiros externos** (manter com marcação explícita ou remover). Total: 16 ocorrências em 8 descrições | `SKILL.md:3` de `typography`, `refactoring`, `microinteractions`, `heuristics`, `cro`, `copy`, `hooked`, `retention` | P1 | P | B (**substitui #7 de A**) | A contou 5/8; são 16. `README.md:128-130` documenta os 6 ausentes como intencionais — só os aliases são defeito puro |
| 10 | **Validar empiricamente o grafo de invocação** antes de qualquer trabalho de conteúdo: `paths:` dispara? o coordinator consegue carregar as 12? o que acontece em Codex/CLI? | `_coordinator/SKILL.md:4`, `README.md:118` | P1 | M | B | `README.md:118` admite que `paths:` é aspiracional. Sem isso, tudo abaixo pode não ter efeito em runtime |
| 11 | Criar `docs/OWNERSHIP.md`: tabela regra→skill dona + prosa resolvendo fronteiras ambíguas | novo | P1 | M | A | Modelo: `jakub AGENTS.md:34-52`. Destrava 12, 13, 14 |
| 12 | Promover `_coordinator` a orquestrador: modos `quick`(cap 5, só HIGH/MEDIUM) e `full`(cap 15), recon de convenções do projeto, tabela de cobertura Domain×Evidence×Result, tratamento de skill indisponível (`Not reviewed`, sem recriar regras de memória), arbitragem de conflito pela skill dona, "Considered but Rejected" (1–3 quick / 2–5 full), read-only por padrão, veredito Block/Needs changes/Approve. **Manter e tornar vinculante** a separação já existente em `:249` | `_coordinator/SKILL.md` | P1 | M | A+B (**reordenado**) | `better-interface/SKILL.md:53`: skills de domínio deferem ao orquestrador. Sem ele definido, os `review-output.md` não têm a quem deferir |
| 13 | Implementar os **três contratos de saída** da §3.1 (Defeito / Experimento / Recomendação); mapear a escala 0–4 de `heuristics` para HIGH/MEDIUM/LOW em vez de aposentá-la; adotar os 8 escalation triggers atravessando os três | `_coordinator`, `audit/heuristics/SKILL.md:197-203`, `audit/cro`, `behavior/*` | P1 | M | **novo** (substitui #10 de A) | A queria uma escala única (destrói informação); B queria dois pacotes (põe `cro` no lado errado). ICE é priorização de experimento, não severidade |
| 14 | Aposentar o bloco "**Goal: 10/10** … rate 0-10" nas **8** skills onde aparece verbatim | `heuristics:22`, `cro:22`, `refactoring:22`, `typography:24`, `microinteractions:20`, `hooked:28`, `retention:37`, `copy:22` | P1 | P | A (**corrigido: 8, não 5**) | Score sem rubrica, idêntico em 8 arquivos, sem consumidor |
| 15 | Escolher **uma** fórmula ICE e remover a outra | `audit/cro/references/testing-methodology.md:202` e `:207` | P1 | P | A | Duas fórmulas produzem prioridades diferentes para os mesmos inputs |
| 16 | Unificar a coluna Priority das duas tabelas 0–4 (`Ignore/Fix if time/…` vs `—/Low/Medium/High/Critical`) e alinhar a ordem das colunas | `audit/heuristics/SKILL.md:197-203`, `references/audit-template.md:19-25` | P2 | P | A (**muito reduzido**) | Não são "dois esquemas de severidade" — é a mesma escala 0–4 com vocabulários de prioridade divergentes |
| 17 | Resolver os **5 conflitos de valor confirmados**: (a) scale no press — escolher entre 0.95/0.96/0.97/0.98; (b) alvo 24/40/44 — adotar a formulação de `hit-areas.md:16`; (c) `ease-in` — `animation-motion:83` proíbe, `visual-polish:326` usa; (d) checklist `animation-motion:495` proíbe as keywords que a tabela `:68-71` prescreve; (e) "Submit" — `trigger-design.md:26,203` proíbe, `case-studies.md` constrói o Caso 1 em cima dele, **na mesma skill** | 6 arquivos | P1 | M | A (**de 12 para 5**) | Ver a1. As outras 7 linhas de A são contextuais, mal enunciadas ou falsas |
| 18 | Resolver por **ownership**, não por edição de valor: line-height corpo, escala de tipo, breakpoints. Uma skill dona; a outra remove ou aponta por nome | `typography` × `refactoring`, `css-implementation.md:347` × `refactoring:100`, `responsive-typography.md:244-249` × `advanced-patterns.md:279-284` | P2 | M | B (**reformulado**) | 1.5–1.75 ⊂ 1.4–1.8: não é contradição. As escalas divergem mas nenhuma é impossível |
| 19 | Adotar `prefers-reduced-motion` como **substituição**: opacity crossfade em vez de slide/scale; matar parallax e autoplay; carrossel inicia pausado; **trocar `animation: none` por `0.01ms`** nos dois snippets que quebram `animationend` | `animation-motion:403`, `:570`, `web-standards:376`, `animation-microinteractions.md:363` | P1 | M | A+B (**corrigido: 4 snippets, não 3**) | `motion-and-zoom.md:39` explica por que `none` trava JS que aguarda o evento |
| 20 | Adicionar `forced-colors` / Windows HCM e a exceção que ela cria para a regra incondicional "Shadows Over Borders" | `foundations/accessibility`, `visual-polish/SKILL.md:93-113` | P1 | M | A+B | `forced-colors`, `prefers-contrast`, `prefers-reduced-transparency`: **zero** ocorrências no plugin |
| 21 | Migrar de WCAG 2.1 para 2.2 (2.4.11, 2.4.13, 2.5.7, **2.5.8**, 3.2.6, 3.3.7, 3.3.8) e adicionar números de SC às regras de `foundations/accessibility` | 11 locais que citam "WCAG 2.1" | P1 | M | A+B | O plugin *anuncia* conformidade (`accessibility:3`); 2.5.8 arbitra o conflito 24/40/44 do item 3 |
| 22 | Limpeza de `web-standards`: unificar as duas seções "Images" (`:168`, `:549`), substituir o UA sniffing (`:855`) por `matchMedia("(pointer: coarse)")`, revisar `-webkit-overflow-scrolling` (`:802`, que já está marcado como deprecated no texto) | `foundations/web-standards/SKILL.md` | P2 | M | A+B (**separado de 5**) | Nenhum é bug de correção |
| 23 | Mover os **17** arquivos hoje alcançáveis só pelo índice final para uma **Quick Reference no topo** de cada `SKILL.md`; só depois remover o índice final | 7 skills, 5.372 linhas (25% do plugin) | P2 | M | A+B (**reescrito**) | Não são órfãos — estão linkados, mas *depois* do checklist. `jakub AGENTS.md:17` proíbe o índice final. A contou 14 e ~943 linhas; são 17 e 5.372 |
| 24 | Criar `review-output.md` por skill + seção `## Reporting` de 2 linhas no fim de cada `SKILL.md`. Começar pelas 4 de `foundations`. Gerar de um template único | 4 skills na primeira leva | P2 | M | A | `AGENTS.md:19`: a seção Reporting fica onde o agente aterrissa antes de escrever a saída. Os 6 `review-output.md` do Jakub compartilham `:9` verbatim — template é viável |
| 25 | Exigir evidência `path/to/file:line` + Before + After + Why em todos os formatos de saída, com a regra anti-formato "nunca linhas separadas Before:/After:" | todos | P2 | P | A | Hoje `file:line` aparece só em `_coordinator:244` e `web-standards:1093` |
| 26 | Tornar review read-only por padrão. Reescrever `heuristics:3` ("Evaluate **and improve**" → "Evaluate"). **Não** mexer em `cro:22` | `audit/heuristics/SKILL.md:3` | P2 | P | A (**escopo reduzido por B**) | B certo sobre `cro:22` (é escopo do rating, não permissão de mutação); errado sobre `heuristics:3`, que está na description sempre carregada |
| 27 | Fazer o `_coordinator` nomear as 12 especialistas explicitamente como downstream, **unidirecional**. Não fazer as 12 chamarem o coordinator | `_coordinator` | P2 | P | B (**substitui #16 de A**) | `jakub AGENTS.md:26,52`: a dependência corre num sentido só, para não criar ciclo |
| 28 | Remover as contagens hard-coded de "13 skills" dos 5 locais; usar formulação que não envelhece | `plugin.json:4`, `marketplace.json:14`, `README.md:3`, `:22`, `:122` | P2 | P | **novo** | `jakub AGENTS.md:62`. Qualquer skill nova quebra os 5 |
| 29 | Alinhar o README com a realidade: `README.md:13` afirma "framework-agnostic" e "rather than boilerplate code" — `accessibility/SKILL.md` tem 630/986 linhas de código, 409 delas JSX | `plugins/ui-excellence/README.md:13` | P2 | P | A | Alegação falsa em dois eixos |
| 30 | Adicionar listas `Triggers on ...` ao frontmatter das 4 skills de `foundations`, seguindo `AGENTS.md:59` (um trigger por branch distinta, sem sinônimos, sem repetir o que o corpo já diz) | 4 `SKILL.md` | P2 | P | A+B | A propôs; B forneceu a regra de autoria correta |
| 31 | Quebrar `web-standards` (1.195) e `accessibility` (985) em `SKILL.md` curto + `references/` | 2 skills | P2 | G | A+B | Depende de 12 (orquestrador define precedência) e de 2/5 (não refatorar código quebrado) |
| 32 | Criar `foundations/color` — dono único de notação, geração de paleta, gamut, medição de par renderizado, tokens semânticos, variantes de aparência. Fronteira: a11y decide *se* falha; color *mede* e *muda*. Princípio "report, don't repaint" | novo | P3 | G | A | `oklch`, `color-mix`, `APCA`, `prefers-contrast`, `forced-colors`: zero ocorrências. Maior lacuna real |
| 33 | Criar `foundations/writing` (~120 linhas + `review-output.md`) e estreitar os triggers de `behavior/copy` | novo + `behavior/copy/SKILL.md:3` | P3 | M | A (**reenunciado por B**) | Enunciado correto: "`behavior/copy` não tem cobertura sistemática de microcopy de interface" — não "não tem nada". `empty state`: zero ocorrências. Corpus: **2.814** linhas |
| 34 | Criar `systems/layout` extraindo `refactoring §2` e `§7` + partes de `advanced-patterns.md`: agrupamento (gap entre grupos ≥ 2× gap interno), primitivas nomeadas, Grid vs Flexbox, **escala de z-index/elevação**, container queries, breakpoints a partir do conteúdo | novo | P3 | M | A | z-index: 2 ocorrências isoladas, nenhuma escala. `visual-polish` anuncia "spacing" no frontmatter e o grupo "Spacing & Hierarchy" do checklist não tem uma regra de espaçamento |
| 35 | Criar `review/interface-review` diff-scoped, incorporando: `merge-base` antes da working tree, ordem two-dot/three-dot preservada, untracked via `ls-files --others`, PR de fork em ref isolado, clone shallow com `--deepen=50/200`, detecção de rename, classificação `Introduced`/`Regression`/`Pre-existing`, pre-existing fora do cap e do veredito, log auditável de toda escrita em `.git` | novo | P3 | G | A+B | Depende de 12, 13, 24. Referências: `scope-resolution.md:39,54,63,81,111`, `interface-review/SKILL.md:35,142`, `removed-signals.md:3,18-28` |
| 36 | Adições pontuais de alto valor/baixo custo: peso de traço de ícone (1.5px/400, 2px/600, um peso por conjunto); ícone na grade nativa no tamanho de render; um SVG com `currentColor`, outline=default/fill=ativo; outline de imagem preto/branco puro nunca neutro tingido; RTL só para ícones direcionais | `visual-polish` (→ `foundations/color` e `systems/layout` quando existirem) | P3 | M | A+B | `better-ui/SKILL.md:60`, `icons.md:84`, `:89`, `surfaces.md:184-193` |
| 37 | Adições de tipografia: `font-weight: 650` em vez de `font-variation-settings`; `font-synthesis: none` como operação perigosa; line-height ≥1.4 para texto que quebra em 3+ linhas; peso ≥400 abaixo de 18px; regra bidi de parágrafo; fork "pergunte, não escolha" no zoom de input iOS | `systems/typography` | P3 | M | A | Jakub é **incondicional** no fork iOS: `details-and-accessibility.md:59` "Ask which one the user wants … do not pick for them". B errou ao querer condicionar |
| 38 | Adições de a11y do `better-accessibility`: navegação SPA (title + foco + scroll); hydration preserva foco e valor; `disabled` nativo vs `aria-disabled`; live region vazia estável antes do texto; submit habilitado até a request começar; nunca bloquear paste; `inert` + `overscroll-behavior: contain` no modal | `foundations/accessibility` | P3 | M | B (**linhas corrigidas**) | `focus-and-keyboard.md:129-131`, `forms.md:84`, `forms.md:77-78` |
| 39 | Adições de cor do `better-colors`: par translúcido testado sobre o conteúdo mais claro e mais escuro; recheck de todo par nas duas aparências; APCA é polarity-aware | `foundations/color` (item 32) | P3 | P | B (**linhas corrigidas**) | `color-usage.md:93`, `:94`, `accessibility-contrast.md:61` |
| 🚫 40 | **Não executar:** "resolver as 12 contradições de valor da §5.1" como escrito | — | — | — | A | 1 é fabricada (prova social — `PERSUASION.md:71` alinha com `dark-patterns.md:328`), 1 não é contradição (line-height), 2 são erros de enunciado de A (breakpoints, escala de tipo), 1 é contextual (3-4 vs 5-10 users). Executar como está insere uma alegação falsa no repo. Ver item 17 |
| 🚫 41 | **Não executar:** "aposentar" a escala 0–4 de `heuristics` e o ICE de `cro` em nome de uma severidade única | — | — | — | A | Instrumentos de domínio com semântica própria. Mapeie (item 13), não delete |
| 🚫 42 | **Não executar:** "fazer os 12 especialistas referenciarem o `_coordinator` (e vice-versa)" | — | — | — | A | Cria o ciclo que `jakub AGENTS.md:26` proíbe. Substituído pelo item 27 |
| 🚫 43 | **Não executar:** deletar `accessibility-depth.md` e a seção de a11y de `krug-principles.md` antes de análise de conteúdo único | — | — | — | A | 518 linhas; é o único local com `aria-pressed` (`:355`) e com o caveat sobre cobertura de ferramentas automatizadas. Consolide primeiro, delete depois |
| 🚫 44 | **Não executar:** "linkar os 14 arquivos de referência órfãos" | — | — | — | A | Não há órfãos: os 52 estão linkados. Substituído pelo item 23 |
| 🚫 45 | **Não executar:** trocar `clip: rect(0,0,0,0)` por `clip-path: inset(50%)` como se fosse correção de bug | — | — | — | A | `web-standards:208` é a receita `.sr-only` padrão e funcional. Preferência estilística |

---

## 5. Confiabilidade dos dois documentos

### Documento A

**Taxa de acerto observada: alta em fatos verificáveis, baixa em contagens agregadas.** Testei 19
citações verbatim do repo do Jakub: **18 exatas**, uma recombinada e apresentada entre aspas (§2.6).
O anexo com as 8 skills do Jakub é **perfeito** — 8/8 nas linhas, 8/8 nas contagens de referência —
e B errou ao atacá-lo. As linhas totais (21.521 e 4.160) batem ao dígito. Os defeitos de código que A
aponta em `web-standards` e `accessibility` são **todos reais** e todos verificáveis. Os dois ratios
de contraste estão errados exatamente como A diz, e A calculou os valores corretos.

**Viés característico: A infla contagens e agrava adjetivos, sempre na direção que fortalece a tese.**
47 references (são 52). 5 handoffs quebrados (são 16). 14 arquivos inalcançáveis (17, e não são
inalcançáveis). ~943 linhas (1.448). 9 lugares com reduced-motion (7 arquivos). 13 multi-routings
(16). 5 skills com o score 0–10 (8). 3 snippets de reduced motion (4). "Defeito mais perigoso do
conjunto" para um erro de tabela consultiva quando há código de teclado quebrado no mesmo plugin. E
uma linha de contradição inteiramente fabricada. O padrão é consistente: **quando A conta, A erra;
quando A cita um arquivo específico, A acerta.**

**Onde confiar sem reverificar:** o anexo do Jakub; as citações verbatim de Jakub (com a exceção da
§2.6); os defeitos de código nomeados na §6 P1; os valores de contraste corrigidos; a tabela §5.3 de
handoffs (o *conteúdo* dela é 16/16 correto — só as contagens no texto ao redor estão erradas); a
tabela §5.4 (14 dos 17 arquivos estão certos); as ausências absolutas (oklch, forced-colors, WCAG 2.2,
sentence case, empty state — todas confirmadas com zero ocorrências). **Onde reverificar sempre:**
qualquer número, qualquer superlativo, e cada linha da tabela §5.1.

### Documento B

**Taxa de acerto observada: alta no raciocínio, ruim nas citações.** B acerta os julgamentos centrais
— 52 references, 2.814 linhas, 16 handoffs, tabela de percentuais somando 100%, breakpoints mal
enunciados, line-height compatível, "órfão" é falso, `paths:` só no coordinator, WCAG 2.1, ICE não deve
ser deletado, o ciclo de invocação, a dependência orquestrador→formato. Essas são objeções de qualidade
alta que A precisava receber.

Mas as `file:line` de B são confiáveis apenas para o **plugin local** (as da seção (c) e a maioria da
(a) batem; `_coordinator:230,244,249` e as seis de `c4` estão exatas). Para o **repo do Jakub** as
citações de B estão **sistematicamente deslocadas 10–20 linhas para baixo** e falham em ~90% dos casos
que testei: `AGENTS.md:48,50,51` (correto: 59, 61, 62), `AGENTS.md:22` (correto: 26, 28),
`AGENTS.md:16` (correto: 17-19), `focus-and-keyboard.md:112` (correto: 131), `forms.md:74` (84),
`color-usage.md:79` (94), `icons.md:70,77` (84, 89), `hit-areas.md:6,14` (11, 16),
`details-and-accessibility.md:48,56` (55, 59), `surfaces.md:13` ✓, `better-layout/SKILL.md:11` (12),
`choosing-fonts.md:24` (30). Em quase todos, a *substância* está certa — o que sugere que B leu o
material mas reconstruiu as linhas de memória ou de outro snapshot.

**Viés característico: B defende o status quo por reflexo e às vezes ultrapassa a evidência para
fazê-lo.** "Melodramático" para os ratios (mas 8.59 licencia um uso AAA que falha). "'Nothing' é falso"
(mas A já tinha feito a ressalva). "Scale(0.95) é modal, remova a linha" (mas A citou outra linha).
"#40 não vale como regra geral" (mas a fonte que B cita diz o contrário, incondicionalmente). E o
erro mais evidente: alegar que `better-typography` tem 108 linhas para desacreditar o anexo de A —
`better-typography/SKILL.md` tem 136; 108 é `better-ui`. B confundiu dois arquivos e construiu uma
objeção inteira em cima disso.

**Onde confiar sem reverificar:** os julgamentos de arquitetura da seção (c) — c1, c2, c5, c7, c9 são
os melhores raciocínios de qualquer um dos dois documentos; as contagens de B (52, 2.814, 16) —
todas confirmadas; as citações de B sobre o plugin local. **Onde reverificar sempre:** toda `file:line`
apontando para `jakub-skills/`, e qualquer afirmação de B sobre o que A disse — B leu A com pressa em
pelo menos três lugares.

### Onde eu discordo dos dois

1. **A e B tratam a §5.1 como triável.** Não é: contém uma alegação inventada (§2.1). Triagem preserva
   o erro; a linha precisa ser deletada.
2. **A e B discutem formato de saída antes de licenciamento.** O item mais urgente do repo não é um
   ratio nem uma escala de severidade — é que o `LICENSE` não reproduz o aviso de copyright do autor
   cujo material `visual-polish` demonstravelmente incorpora, enquanto o README chama esse mesmo
   material de "Original content" (§2.2).
3. **A e B ignoram que o modelo de dois pacotes já existe** em `_coordinator:240` + `:249`. O trabalho
   não é inventá-lo — é torná-lo vinculante, e corrigir a partição, porque `cro` não pertence a nenhum
   dos dois lados que B propôs (§3.1).
