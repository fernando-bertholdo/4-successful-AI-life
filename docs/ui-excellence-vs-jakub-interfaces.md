# ui-excellence vs. jakubkrehel/skills (`interfaces`) — análise comparativa e backlog

**Data:** 2026-08-13
**Escopo analisado:** 100% dos arquivos dos dois plugins.

| | `ui-excellence` (Fernando) | `interfaces` (Jakub Krehel) |
|---|---|---|
| Repo | `fernando-bertholdo/4-successful-AI-life` → `plugins/ui-excellence` | `jakubkrehel/skills` (raiz = plugin + marketplace) |
| Versão | `1.0.0-alpha.3` | `1.1.0` |
| Skills | 13 (12 especialistas + `_coordinator`) | 8 (6 domínios + 1 orquestrador + 1 review de diff) |
| Linhas de markdown | **21.521** | **4.160** |
| Arquivos de referência | 47 | 27 |
| Distribuição | plugin Claude Code | plugin Claude Code **+** `npx skills add` **+** opencode |

O `ui-excellence` tem **5,2× mais conteúdo** e cobre domínios que o Jakub nem toca (CRO, hábito, retenção, heurísticas de usabilidade). O `interfaces` tem **muito mais rigor operacional**: cada regra tem dono único, cada skill sabe produzir um relatório auditável, e nada se contradiz. As duas coleções falham em coisas opostas.

---

## 1. Sumário executivo

**Três conclusões.**

1. **O problema do `ui-excellence` não é cobertura, é governança.** Você tem mais conteúdo técnico que o Jakub em quase todo domínio. Mas 9 arquivos diferentes prescrevem contraste, 6 prescrevem duração de animação, 3 dão valores *incompatíveis* para `scale` no press, e 4 esquemas de severidade mutuamente inconsistentes convivem no mesmo plugin. Um agente que carrega duas skills suas ao mesmo tempo recebe instruções conflitantes.

2. **O `interfaces` inventou seis mecanismos estruturais que você não tem** — e são baratos de adotar: dono único por regra, `review-output.md` separado do `SKILL.md`, escala de severidade compartilhada com *escalation triggers*, exigência de evidência `path:linha`, seção "Considered but Rejected", e veredito `Block`/`Needs changes`/`Approve`. Nenhum deles exige reescrever conteúdo.

3. **Existem 2 erros factuais que precisam sair hoje**, independente de qualquer refatoração — dois ratios de contraste publicados na tabela de referência de `foundations/accessibility` estão numericamente errados (ver §6).

**A oportunidade estratégica:** o Jakub é deliberadamente estreito (só interface). Você cobre interface *e* comportamento/conversão. Se o `ui-excellence` adotar o rigor operacional dele **sem** abrir mão da amplitude, ele fica sem concorrente direto — porque hoje ninguém entrega "audit de UI + audit de conversão + audit de retenção" com formato de saída unificado.

---

## 2. As duas arquiteturas

### Como o Jakub organiza uma skill

```
skills/better-typography/
├── SKILL.md              ← 136 linhas. Frontmatter (só name + description
│                            com lista "Triggers on ..."), H1 editorial,
│                            parágrafo de filosofia, parágrafo de HANDOFF
│                            nomeando as skills irmãs, Quick Reference
│                            (tabela → arquivos), Core Principles numerados,
│                            Common Mistakes (tabela), seção Reporting.
├── choosing-fonts.md     ← profundidade: receitas, tabelas de lookup
├── css-cheat-sheet.md
├── spacing-and-sizing.md
├── wrapping-and-punctuation.md
├── details-and-accessibility.md
├── review-output.md      ← formato de relatório, SEPARADO do SKILL.md
└── agents/openai.yaml    ← display_name + short_description (Codex)
```

**Regra de ouro declarada no `AGENTS.md` dele:** *"A principle states the rule and links out for the recipe; it never restates the reference file in shorter form, and the reference file never restates the principle in longer form."*

E: *"Each rule lives in exactly one skill; other skills point to it by skill name in backticks, never via cross-skill relative links."*

### Como o `ui-excellence` organiza

Duas gerações misturadas:

- **`foundations/*` (autoria sua):** tudo inline, sem `references/`, sem progressive disclosure. `web-standards/SKILL.md` tem **1.195 linhas**; `accessibility/SKILL.md` tem **985**, das quais ~450 são componentes React.
- **`systems/`, `audit/`, `interaction/`, `behavior/` (adaptados do wondelai):** têm `references/`, mas a ligação é frouxa — em `refactoring`, **6 de 7 seções apontam para o mesmo arquivo** e 3 dos 5 references nunca são linkados do corpo (≈943 linhas inalcançáveis pelo caminho de leitura).

### Comparação estrutural

| Mecanismo | `interfaces` | `ui-excellence` |
|---|---|---|
| Frontmatter | `name` + `description` com lista `Triggers on ...` | 2 dialetos (foundations: 2 chaves; wondelai: + `license` + `metadata`) |
| Progressive disclosure | Sistemático, `SKILL.md` curto (79–187 linhas) | Ausente em `foundations`; parcial e quebrado nos demais |
| Dono único por regra | Tabela explícita de ownership no `AGENTS.md` | Inexistente — média de 4 donos por regra |
| Handoffs entre skills | Explícitos, bidirecionais, por nome em backticks | Quebrados (5 apontam para skills inexistentes) ou anônimos ("use design system docs") |
| Formato de relatório | `review-output.md` por skill + formato consolidado no orquestrador | 2 formatos incompatíveis em 2 das 13 skills |
| Escala de severidade | Uma, compartilhada, com 8 escalation triggers | 4 incompatíveis |
| Evidência obrigatória | `path/to/file:line` + Before + After + Why | Só em `web-standards` e no `_coordinator` |
| Veredito | `Block` / `Needs changes` / `Approve` | Score 0–10 sem rubrica (5 skills, texto idêntico) |
| Restrição de escopo | "Review é read-only por padrão" | Nenhuma; as duas skills de audit são explicitamente "evaluate **and improve**" |
| Review de diff/PR | Skill dedicada (`interface-review`) | Inexistente |

---

## 3. Os seis mecanismos que valem copiar

### 3.1 Dono único por regra (`AGENTS.md` → tabela de ownership)

O Jakub mantém uma tabela que diz exatamente quem manda em quê, e resolve as fronteiras ambíguas em prosa:

> `better-accessibility` decide *quando* contraste é exigido e *se* o par falha; `better-colors` mede o par renderizado e muda as cores.
> `better-accessibility` é dono de estrutura semântica de heading; `better-typography`, de como os níveis renderizam visualmente.
> `better-typography` é dono da mecânica de truncamento; `better-layout`, de se o layout ao redor tem espaço; `better-writing`, do texto de origem.
> `better-accessibility` é dono do requisito de reduced-motion; `better-ui`, da receita opcional de animação.

**Por que isso importa mais para você do que para ele:** você tem 12 especialistas contra 6 dele. Sem tabela de ownership, o `_coordinator` roteia "Full page audit → ALL foundations + heuristics + refactoring" e entrega ao agente 5 arquivos que discordam sobre `scale` no press, tamanho de alvo, duração de animação e altura de linha.

### 3.2 `review-output.md` separado do `SKILL.md`

Racional dele, verbatim: *"These skills fire mostly on build tasks, where the format is dead weight in context."*

Duas coisas alcançam o arquivo: uma linha na Quick Reference e uma seção `## Reporting` de duas linhas no fim do `SKILL.md`. E ele explica por que as duas: *"The Reporting section is what makes the pointer fire, because it sits where the agent lands before writing output; the Quick Reference row alone is read while orienting and misses that moment."*

### 3.3 Severidade compartilhada + escalation triggers

Uma escala (`HIGH`/`MEDIUM`/`LOW`) e — o detalhe realmente inteligente — **8 gatilhos que são `HIGH` na hora, sem discussão**:

- controle interativo sem nome acessível
- controle alcançável por teclado sem indicador de foco visível
- caminho alcançável por ponteiro mas não por teclado
- movimento que ignora `prefers-reduced-motion`
- conteúdo cortado/inalcançável em 320px ou 200% zoom
- par de contraste de texto de corpo que falha o requisito
- estado ou significado carregado só por cor
- ação destrutiva sem confirmação, undo ou tratamento distinto

E a regra que protege o relatório: *"a cap may shorten a report but may never be why a blocker went unreported."*

### 3.4 Evidência obrigatória

Toda finding: `path/to/file:line` + Before + After + Why. Regra anti-formato repetida verbatim nos 6 `review-output.md`: **"Never use separate 'Before:' / 'After:' lines."** E consolidação: uma causa-raiz = uma linha, listando todos os locais.

### 3.5 "Considered but Rejected"

Seção obrigatória (1–3 candidatos em `quick`, 2–5 em `full`) com o que foi inspecionado e deliberadamente **não** virou finding. Motivos aceitos: a skill dona permite a implementação atual, evidência insuficiente, a convenção do projeto é defensável, ou a mudança adicionaria complexidade sem benefício.

Isso resolve o vício mais comum de agente revisor: inventar problema para parecer útil.

### 3.6 Read-only por padrão + "Not verified"

*"Treat a review request as read-only. Do not edit source code unless the user also asks to implement the findings."*
*"If a check cannot be run, label it **Not verified** and state what remains; never convert a verification gap into a finding."*

Hoje suas duas skills de audit dizem literalmente o contrário: `heuristics` = "Evaluate **and improve**", `cro` = "When reviewing **or creating**".

---

## 4. Convergência domínio a domínio

Legenda: 🟢 você está à frente · 🟡 empate com problemas · 🔴 lacuna real

### 🟡 Tipografia — `systems/typography` vs `better-typography`

**Você tem e ele não:** fórmula de geração de escala fluida com `clamp()`, escala de 8 degraus pronta, comando `pyftsubset` com unicode ranges, `size-adjust`/`ascent-override` para métricas de fallback, tabela de distância de leitura, orçamentos de payload (<50KB/peso, <200KB total), percentuais de suporte de browser.

**Ele tem e você não:**

| Tema | Prescrição dele |
|---|---|
| Propriedades vs. raw tags | `font-weight: 650` **não** `font-variation-settings: "wght" 650` — porque a segunda "silenciosamente não faz nada" em fallback não-variável |
| `font-synthesis` | Tratado como perigoso: só depois de verificar toda a pilha de fallback. *"Disabling synthesis is not a diagnostic and must not erase emphasis"* |
| Peso mínimo por tamanho | Abaixo de `18px`, peso `400`+; pesos <300 só display (`28px`+) |
| Line-height mínimo | Qualquer texto que quebra em 3+ linhas precisa de ≥`1.4`, mesmo em linha de altura restrita |
| Truncamento | Se o texto escondido importa, o valor completo precisa ficar alcançável (tooltip ou expandido) |
| Zoom de input no iOS | **Pergunta ao usuário qual das duas correções** em vez de escolher: `text-base sm:text-sm` ou `16px` + `transform: scale(0.8125)` com wrapper (a matemática exata está lá) |
| `text-box` | `trim-both cap alphabetic` — Chromium 133+, Safari 18.2+, sem Firefox, tratar como progressive enhancement |
| Bidi | Snippet de 1–2 linhas segue a direção da UI; parágrafo de 3+ linhas alinha à direção do próprio script. Nunca inverter dígitos; `<bdi>` para valores mistos |
| Underline | `text-underline-position: from-font` + `from-font` thickness; só a cor anima de forma confiável — para animar mais, construir como elemento separado |
| Restrição de escopo | *"Applying or reviewing typography never requires a new typeface... do not introduce a paid or proprietary face just to satisfy a review checklist"* |

**Problemas seus neste domínio:** CSS inválido publicado como copy pattern (`h1, h2 { line-height: 1.1-1.25; }` — range não é valor CSS; um agente que copiar isso emite declaração morta). Dois handoffs quebrados, um para skill inexistente (`top-design`). Compete com `refactoring` §3 em escala e line-height sem arbitragem (1.4–1.8 vs 1.5–1.75 para corpo).

### 🔴 Cor — **maior lacuna do plugin**

Nenhuma skill sua é dona de cor. O que existe está espalhado por `refactoring` §4, `theming-dark-mode.md`, `data-visualization.md`, `accessibility` e `visual-polish`.

**Ausente por completo:**

- **OKLCH / LCH / OKLab** — zero ocorrências no plugin inteiro
- P3 / wide gamut / sintaxe `color()`; `color-mix()`; relative color syntax
- Método sistemático de geração de paleta (você tem uma heurística HSL: "mais claro = lightness maior + saturação menor + hue em direção a 60°")
- Arquitetura de token semântico em nível de plugin
- **`forced-colors` / Windows High Contrast Mode** — e isso quebra silenciosamente a regra incondicional "shadows over borders" de `visual-polish`, porque `box-shadow` desaparece em forced-colors
- `prefers-contrast` / `prefers-reduced-transparency`
- Derivação de cor de acento/marca

**O que o `better-colors` prescreve que é diretamente aproveitável:**

| Regra | Valor |
|---|---|
| Fronteira claro/escuro | L > 0.73 → texto escuro |
| Gap de lightness (fundo claro) | fg L < 0.35 quando bg L > 0.9 |
| Gap de lightness (fundo escuro) | fg L > 0.9 quando bg L < 0.25 |
| Hue drift | >10° de variação entre degraus da paleta = drift visível |
| APCA corpo | \|Lc\| ≥ 75 mínimo, ≥ 90 preferido |
| APCA não-corpo | \|Lc\| ≥ 60 mínimo; large text ≥45; componentes UI ≥30; piso absoluto Lc 15 |
| Chroma máximo em sRGB @L=0.5 | roxo (H≈285) C≈0.29 · vermelho-laranja C≈0.20 · ciano (H≈195) C≈0.09 |
| Uma cor, um significado | Tolerância numérica: **±15° de hue** |
| Variante de alto contraste | Alarga o gap de lightness em **≥0.15 L** sobre o default |
| Modo escuro | Trocar os *papéis semânticos* primeiro, nunca inverter mecanicamente cada degrau |

E o princípio que mais falta no seu plugin: **"Report, don't repaint."** — quando um check falha, reportar o par, o Lc medido e o threshold que falta, e **deixar as cores como estão**. Cor é decisão de design; só mudar quando pedido.

### 🔴 Layout

**Mapeia para:** `refactoring` §7 (magro: left-align por padrão, sidebars 240–320px, `grid grid-cols-3 gap-6`) + §2 (escala 4/8/16/24/32/48/64 — seu único sistema de espaçamento) + `advanced-patterns.md` (breakpoints) + `web-standards` (safe areas, `min-w-0`).

**Ausente:**

- Sistema de grid (sem 12 colunas, sem `minmax`, sem `auto-fit`)
- **Decisão Grid vs. Flexbox** — `visual-polish` literalmente desvia: "use CSS Grid/Flexbox guides"
- Primitivas de layout nomeadas (stack, switcher, sidebar, cluster, cover)
- Container queries como ferramenta de layout (só aparecem dentro de `responsive-typography.md`)
- **Escala de z-index / elevação** — ausente do plugin inteiro
- `visual-polish` anuncia "spacing" no frontmatter e seu grupo de checklist "Spacing & Hierarchy" **não tem uma única regra de espaçamento**
- Dois conjuntos de breakpoint discordantes (1280/1536 vs 1440)

**Regras dele que resolvem isso com pouco texto:**

- Agrupar com espaço, não com linha: **o gap entre grupos ≥ 2× o gap dentro do grupo** (`8px` intra → `16px`+ inter)
- Uma etapa de espaçamento por nível de subordinação (`16px` como default útil)
- Sem sistema de densidade estabelecido: **`12px` entre controles com borda/preenchidos; `24px` de folga ao redor de controles sem borda** — e explicitamente *aditivo* aos hit areas do `better-accessibility`, para que áreas expandidas nunca se sobreponham
- Conteúdo escondido precisa de pista visível: **deixar o próximo item aparecer `16–32px` além da borda de scroll**
- Breakpoints vêm do conteúdo, não de preset: *"colapsar tarde"*, testar **o menor e o maior tamanho primeiro**
- Rótulo de disclosure diz o que está escondido: "Show 12 more results", não "More"
- Botões dimensionam pelo rótulo via `padding-inline`, **nunca largura fixa**
- *"If a modal's content scrolls, its action row doesn't."*

### 🔴 UX Writing — nenhum dono

Seu conteúdo de copy está fragmentado em 4 skills e 3 diretórios, sem arbitragem. `web-standards` manda **Title Case (Chicago)** para headings e botões; `heuristics` e `COPYWRITING.md` não tocam no assunto; sentence case (a convenção moderna dominante em produto) nunca é discutida.

E — resultado que vale registrar — **`behavior/copy` NÃO cobre esse terreno.** A análise dos 2.823 linhas de `copy` mostrou:

| Categoria | Fatia de `copy` |
|---|---|
| Marketing / posicionamento / brand | ~45% |
| Vendas e outbound | ~15% |
| Storytelling / ops de conteúdo | ~15% |
| Apresentações / pitch | ~8% |
| Comunicação interna e processo org | ~7% |
| Case studies históricos | ~10% |
| **Microcopy de interface** | **~3–5%** |

`copy` não tem **nada** sobre: mensagens de erro (uma menção de passagem, zero exemplos), empty states (a expressão não aparece no arquivo), rótulos de botão/CTA, labels de formulário/placeholder/helper text, diálogos de confirmação, toasts, tooltips, estados de loading, limites de caracteres/i18n, sentence vs title case, glossário de terminologia, alt text.

Pior: os triggers de `copy` ("value proposition", "tagline", "make it memorable") são largos o bastante para ele ser invocado num pedido de copy de interface — e aí ele dá o conselho **errado**, porque surpresa, curiosity gap e storytelling emocional são ativamente danosos numa mensagem de erro.

**O `better-writing` do Jakub é uma skill de 115 linhas, sem references, e cobre exatamente o que falta.** Os 12 princípios (resumo dos mais valiosos):

- Recon da voz existente **antes** de escrever — e: *"Treat a difference from generic plain language as a finding only when it creates inconsistency, ambiguity, translation risk, or an inappropriate tone"*
- Tabela de tom por superfície: sucesso/onboarding/empty = caloroso, pode ser leve; ações de rotina/settings = neutro; erros/confirmações destrutivas = calmo, **zero jocosidade**; perda de dados/segurança = sério e explícito
- "Você", não "o usuário". **"Unable to load content" em vez de "We're having trouble loading this content"**
- Verbos de dispositivo: "tap" em touch, "click" com ponteiro, "select" quando ambos
- Nunca concatenar fragmentos em torno de variáveis (`"You have " + n + " new messages"`) — ordem de palavras muda por idioma
- Botões começam com verbo; confirmação repete a consequência: "Delete this project?" → `Delete project` / `Cancel`
- Vocabulário de fluxo consistente: "Continue" **ou** "Next", escolha um
- Uma política de capitalização **por tipo de elemento**; **sentence case é o default mais seguro**
- Settings descrevem o estado ON ("Send read receipts", nunca a negativa)
- Erro é uma instrução adjacente ao campo que falhou. Sem culpa, sem "oops", sem exclamação. E: *"If the same error keeps firing for many users, redesign the interaction instead of rewording it."*
- Empty state orienta e aponta para frente, com uma ação. Busca vazia nomeia a query: "No results for 'quarterly'. Clear filters"
- Placeholder é exemplo, nunca label

### 🟡 UI polish — `visual-polish` + `refactoring` + `microinteractions` vs `better-ui`

Aqui você tem **muito** mais: 5 case studies totalmente especificados em `microinteractions/references/case-studies.md` (formulário, toggle, pull-to-refresh, loading, toast — com valores de cor, timing, ARIA, debounce, limites de stack), tabelas de estados, guia de seleção de indicador de progresso, thresholds de percepção.

**Mas:** `case-studies.md` é **órfão** — nenhum link do corpo do `SKILL.md` chega nele. É o arquivo mais prescritivo do plugin e o menos alcançável.

**Refinamentos dele que valem incorporar:**

- Raio concêntrico: você diz `outer = inner + padding`, `advanced-patterns.md` diz `nested = outer − padding`. São a mesma regra escrita de duas formas — unificar.
- Outline de imagem: **preto puro em light (`oklch(0 0 0 / 0.1)`), branco puro em dark**, nunca um neutro tingido — *"a tinted outline picks up the surface color underneath it and reads as dirt on the image edge"*. Seu `visual-polish` só diz `rgba(0,0,0,0.1)`.
- Peso de traço de ícone acompanha o peso do texto: **`1.5px` ao lado de 400, `2px` ao lado de 600**; um peso por conjunto; nunca misturar bibliotecas na mesma superfície. (Seu plugin tem tamanhos de ícone, mas nada sobre stroke weight ou optical size.)
- Um SVG com `currentColor`, estados por CSS. Outline = default, fill = estado ativo.
- Transição de ícone: `scale 0.25→1`, `opacity 0→1`, `blur 4px→0`; com motion library `{ type: "spring", duration: 0.3, bounce: 0 }` — **bounce sempre 0**; sem library, manter os dois ícones no DOM (um absoluto) e cross-fade com `cubic-bezier(0.2, 0, 0, 1)`.
- *"Motion is never the only feedback channel; every animated state change also needs a static cue (color, icon, label)."*
- Método de review: *"replay motion at 10% speed in the browser's Animations panel and walk every state"* — você tem isso em `animation-motion` (Animations panel @10x), ele generalizou para toda a skill.

### 🟢🔴 Acessibilidade — mais volume, menos utilidade

Você tem **cinco vozes de a11y** (`foundations/accessibility` 985 linhas · `heuristics/references/wcag-checklist.md` · `foundations/web-standards` · `refactoring/references/accessibility-depth.md` inalcançável · `krug-principles.md`). Nenhuma delas se referencia.

**Lacunas concretas:**

- **WCAG 2.2 ausente das cinco.** É Recomendação W3C desde outubro/2023; arquivos datados de 2026-03-30 ainda miram só 2.1. Faltam: 2.4.11 Focus Not Obscured, 2.4.13 Focus Appearance, 2.5.7 Dragging Movements, **2.5.8 Target Size (Minimum)** — que arbitra diretamente sua contradição 40 vs 44 —, 3.2.6, 3.3.7, 3.3.8.
- A skill principal de a11y cita **zero números de SC**, então nenhuma finding pode virar relatório de conformidade. (O ledger SC-por-SC existe — em `heuristics/references/wcag-checklist.md`, que nem é linkado do corpo da própria skill.)
- `prefers-reduced-motion` **não aparece** na skill de acessibilidade (aparece em 9 outros lugares, com 3 snippets incompatíveis).
- `:focus-visible` não aparece nela (só em `web-standards`, que diz para preferi-lo).
- `forced-colors` / Windows HCM: ausente em todo o plugin.
- Sem `inert`, `aria-current`, `aria-pressed`, `aria-busy`, `aria-sort`, `aria-activedescendant`; sem a11y de tabela de dados (`<th scope>`, `<caption>`); sem `<fieldset>/<legend>` (só em `web-standards`); sem elemento `<dialog>`; sem combobox/accordion/tree/slider.
- Critério de aceite "zero axe violations, Lighthouse ≥90" convida a tratar aprovação automatizada como conformidade — e o caveat honesto ("axe pega ~30%, ferramentas automatizadas perdem ~70%") existe só no arquivo inalcançável.

**Do `better-accessibility`, o que mais falta em você:**

- Hit area ancorado no critério certo: *"WCAG 2.5.8's Level AA baseline is a 24×24 CSS-pixel target or one of its defined spacing, equivalent-control, inline, user-agent, or essential exceptions. For easier activation, aim for 44×44px in touch contexts and 40×40px in desktop interfaces when density permits."* — **isso reconcilia seus 40 e 44 numa frase.**
- Foco: estilizar `:focus-visible`, preferir o indicador nativo, verificar o indicador completo contra **cada cor adjacente que ele cruza**, ≥`2px` sólido, preservar cores de sistema em forced-colors.
- Modal: `inert` no fundo + `overscroll-behavior: contain` + devolver foco ao trigger.
- Botão de submit **fica habilitado** até a request começar; validar no submit; `aria-invalid` + `aria-describedby` + focar o primeiro campo inválido. Nunca bloquear paste.
- `disabled` nativo vs `aria-disabled="true"` — quando usar cada um, e que com `aria-disabled` é preciso bloquear ponteiro, teclado e comportamento de form em código.
- Live regions: `role="status"` polido para atualizações não urgentes, `role="alert"` só para erro urgente; **renderizar uma região vazia estável antes de atualizar o texto** para anúncios repetidos confiáveis.
- Reduced motion como **substituição**, não como matar tudo: *"replace slides and scales with opacity crossfades; kill parallax and autoplay entirely"* + toasts com ação ou erro **permanecem até serem dispensados**. Seu plugin trata reduced-motion como kill-switch em todos os 9 lugares.
- Zoom: 200% e reflow em 320px sem scroll horizontal; `min-height` em vez de `height` fixa; não capar zoom no viewport meta.

### 🔴 Orquestração — `_coordinator` vs `better-interface`

O seu `_coordinator` roteia bem por intenção (13 combinações de multi-routing, sinais por arquivo e por palavra-chave). O que falta é tudo que vem **depois** do roteamento.

| | `better-interface` | `_coordinator` |
|---|---|---|
| Modos | `quick` (5 findings, só HIGH/MEDIUM) e `full` (15) | — |
| Recon antes de julgar | Identifica framework, tokens, viewports; lê `CONTRIBUTING.md`/`AGENTS.md`/design-system docs e **nomeia no output** o que achou | — |
| Ordem de review | Fixa: a11y → layout → writing → typography → colors → ui, "so foundational failures are not hidden by polish" | Tem ordem de prioridade (9 passos) ✓ |
| Skill indisponível | Marca o domínio `Not reviewed`, nomeia a skill faltante, **não recria as regras de memória** | — |
| Conflito entre skills | Atribui à skill dona da regra subjacente, menciona efeito secundário na coluna Why, reporta **uma vez** | — |
| Cobertura declarada | Tabela Domain × Evidence inspected × Result | — |
| Restrição | Read-only por padrão | — |
| Veredito | Block / Needs changes / Approve | Score 0–10 sem rubrica |

E a linha que resume a diferença de postura: *"Read them for leverage, not permission. A documented convention is not evidence the convention is good, and 'it's in the style guide' does not retire a finding. What they change is **where** you report: when a guideline or shared token is the cause, report it once against that source with the components as its locations."*

### 🔴 Review de diff — lacuna estrutural limpa

Nenhuma das suas 13 skills é diff-scoped. Nenhuma menciona git, arquivos alterados, branch base, ou "revise só o que mudou".

O `interface-review` dele resolve isso com ideias que valem por si:

- **Resolução de escopo com ordem definida:** `merge-base` primeiro, working tree depois. *"Order matters: checking the working tree first lets one stray formatting edit shadow a twelve-commit branch while the report still claims full coverage."*
- **Sem mudança, perguntar em vez de inventar uma.** Nunca cair em `HEAD~1..HEAD` por conta própria.
- **Blast radius:** um arquivo alterado é evidência, não o sujeito do review. Expandir 1 hop (importers diretos); 2 hops só para design tokens e primitivas. Máximo 5 consumidores, e **dizer quantos não foram expandidos**.
- **Ler o lado `-` do diff.** Regressões são invisíveis no estado pós-mudança.
- **Classificar toda finding:** `Introduced` / `Regression` / `Pre-existing` — por *o que o diff tocou*, confirmado com `git blame` contra o base ref.
- **Segurar a mudança contra a intenção declarada** (título do PR, issue, commits) — é o que revela a mudança *incompleta*: variante nova aplicada a alguns estados mas não a todos, string nova sem entrada no catálogo de tradução, componente novo sem empty/loading/error.
- **Nunca mutar a working tree.** `git fetch` é permitido (só escreve em `.git`); `gh pr checkout`, `git checkout`, `git switch`, `git stash` nunca. Review renderizado usa `git worktree add /tmp/review-<n>`.
- Findings `Pre-existing` ficam **fora do cap e fora do veredito** — tocar num arquivo legado não vira auditoria do arquivo inteiro.

---

## 5. Conflitos internos que a comparação expõe

Estes existem independentemente do Jakub. A comparação só os tornou visíveis.

### 5.1 Contradições diretas de valor

| Regra | Valores conflitantes | Onde |
|---|---|---|
| Scale no press | **0.97** @160ms `cubic-bezier(0.23,1,0.32,1)` · **0.96** @100ms `cubic-bezier(0.4,0,0.2,1)` · 0.97 @50–100ms · 0.97 @100–150ms · "2%" · `active:scale-95` | `animation-motion` · `visual-polish` §11 · `feedback-patterns.md` · `animation-microinteractions.md` · `trigger-design.md` · `advanced-patterns.md` |
| Tamanho de alvo | **40×40** vs **44×44** | `visual-polish` §13 vs `web-standards` (+5 outros com 44) |
| Orçamento de duração | "**under 300ms**" · "200–400ms micro / 500–800ms page" · **800ms** para entradas | `animation-motion` · `web-standards` · `visual-polish` §9 |
| `ease-in` | "**Never use `ease-in` for UI animations**" (duas vezes) | `animation-motion` vs `visual-polish` §10 (`exitSubtle 400ms ease-in`) |
| Stagger | 50ms · 80ms · 100ms · `i*0.08` · `i*0.1` | 4 valores, dois deles no mesmo arquivo |
| Line-height corpo | 1.4–1.8 vs 1.5–1.75 | `typography` §5 vs `refactoring` §3 |
| Escala de tipo | rem (.75/.875/1/1.125/1.25/1.5/2/2.5) vs px (12/14/16/20/24/30/36) | `css-implementation.md` vs `refactoring` §3 |
| Breakpoints | 640/768/1024/1280/1536 vs 640/1024/1440 | `advanced-patterns.md` vs `responsive-typography.md` |
| `#374151` em branco | **10.5:1** vs **9.1:1** (valor real: **10.31:1**) | `refactoring` §4 vs `accessibility-depth.md` — dentro da mesma skill |
| Teste de usabilidade | "**3-4 users**" vs "**5-10 users**" | `krug-principles.md` vs `RESEARCH.md` |
| Prova social fabricada | Endossada como trigger de Social Proof vs. nomeada como dark pattern | `PERSUASION.md` vs `dark-patterns.md` |
| Rótulo "Submit" | "Avoid vague labels like 'Submit'" vs. case study inteiro construído em torno de um botão "Submit" | `trigger-design.md` vs `case-studies.md` Case 1 |

`animation-motion` também se contradiz sozinho: o checklist exige "Not using CSS `ease`, `ease-in`, or `ease-out` defaults" enquanto a tabela Q3 prescreve exatamente essas keywords por cenário.

### 5.2 Vocabulários de severidade incompatíveis

Quatro esquemas convivem:

1. `heuristics` SKILL.md — 0 a 4 (Not a problem → Catastrophic), com fatores Frequency/Impact/Persistence
2. `heuristics/references/audit-template.md` — Low/Medium/High/Critical, colunas invertidas
3. `cro` — ICE 1–10 (com **duas fórmulas competindo**: `(I+C+E)/3` e `(I×2 + C×1.5 + E×1)/4.5`) + valor de oportunidade
4. `_coordinator` — Must Fix / Should Fix / Polish / Engagement

O `_coordinator` ativa dois ou três desses simultaneamente em várias rotas, sem reconciliação.

### 5.3 Handoffs quebrados

Todos os cinco frontmatters do wondelai apontam para nomes que não existem no plugin:

- `typography` → `refactoring-ui` [é `refactoring`], `top-design` [**não existe**]
- `refactoring` → `web-typography` [é `typography`], `ux-heuristics` [é `heuristics`]
- `microinteractions` → `refactoring-ui`, `design-everyday-things` [**não existe**]
- `heuristics` → `refactoring-ui`, `cro-methodology` [é `cro`]
- `cro` → `one-page-marketing` [**não existe**], `ux-heuristics`
- `copy` → `storybrand-messaging` [**não existe**], `contagious` [**não existe**]
- `hooked` → `improve-retention` [nome antigo de `retention`], `contagious`
- `retention` → `hooked-ux` [nome antigo de `hooked`], `drive-motivation` [**não existe**]

Em `foundations`, os handoffs são anônimos: "use dedicated motion library docs", "separate A11y guide", "use design system docs" — existem irmãs para pelo menos três, nenhuma é nomeada. `foundations/accessibility` não tem **nenhuma** referência cruzada.

E: **nenhum dos 12 especialistas referencia o `_coordinator`.**

### 5.4 Referências inalcançáveis

| Skill | Arquivos nunca linkados do corpo |
|---|---|
| `refactoring` | `animation-microinteractions.md`, `accessibility-depth.md`, `data-visualization.md` (~943 linhas) |
| `microinteractions` | `case-studies.md` — o arquivo mais prescritivo do plugin |
| `heuristics` | `audit-template.md` (o único artefato de output), `wcag-checklist.md`, `cultural-ux.md` |
| `cro` | `funnel-analysis.md`, `COPYWRITING.md` |
| `hooked` | `neuroscience-foundations.md`, `case-studies.md` |
| `retention` | `behavior-model.md`, `product-applications.md`, `case-studies.md` |

---

## 6. Correções factuais — fazer antes de qualquer refatoração

**P0 — errado e perigoso:**

1. **`foundations/accessibility`, tabela "Contrast Ratio Quick Check": duas de quatro linhas têm ratios numericamente errados.**
   - `#0066cc` sobre `#fff` está listado como **8.59:1** — o valor real é ≈ **5.57:1**
   - `#555` sobre `#fff` está listado como **9.26:1** — o valor real é ≈ **7.46:1**
   Uma tabela de referência de contraste com números errados é o defeito mais perigoso do conjunto.

2. **`visual-polish` §13** — "at least 40×40 pixels (**mobile accessibility standard**)". Não existe esse padrão. WCAG 2.2 SC 2.5.8 = 24×24 (AA), SC 2.5.5 = 44×44 (AAA), Apple HIG 44pt, Material 48dp.

3. **`animation-motion` Common Mistake 1** — "submitted 100x/day, animation compounds to ~3 min/day lost" para uma animação de 300ms. 100 × 300ms = **30 segundos**. O argumento do frequency gate está apoiado nessa conta.

**P1 — código quebrado ou obsoleto:**

- `web-standards`: `import { useQueryState } from "next-usp"` — **`next-usp` não é um pacote real** (a prosa recomenda `nuqs`). Passa `priority` para um `<img>` cru (prop exclusiva do `<Image>` do Next). Adiciona `onKeyDown` Enter/Space a um `<button>` nativo (dispara duas vezes). Retorna `<html lang={...}>` de dentro de um componente e computa `navigator.language` durante render — causando exatamente o hydration mismatch que a própria seção de Hydration Safety alerta. `-webkit-overflow-scrolling: touch` obsoleto desde iOS 13. `clip: rect(0,0,0,0)` superado por `clip-path: inset(50%)`. UA sniffing `/iPhone|iPad|Android/` em vez de `matchMedia("(pointer: coarse)")`. Duas seções `Images`.
- `accessibility`: o Dropdown liga `onKeyDown` ao `<ul>` mas nada dentro recebe foco (sem roving tabindex, sem `aria-activedescendant`, sem `.focus()`) — as setas nunca disparam. Põe `aria-selected` em `role="menuitem"`, não suportado. O Modal restaura o foco duas vezes; o seletor de focáveis omite `[contenteditable]`, `details`, `iframe` e não exclui `disabled`/`hidden`; sem `inert` no fundo, sem scroll lock. O exemplo Jest tem `expect(lastButton === document.activeElement);` — **assertion sem matcher, passa sempre em silêncio**.
- CSS inválido publicado como copy pattern: `typography/SKILL.md` (`line-height: 1.1-1.25`), `data-visualization.md` (`.bar-gap: 8px` — propriedade inventada).
- `testing-methodology.md` lista Google Optimize com a nota "Sunsetting" — encerrou em setembro/2023.

---

## 7. Skills novas propostas

### 7.1 `foundations/color` — **prioridade máxima**

A maior lacuna. Não existe hoje e o conteúdo espalhado não substitui.

Escopo sugerido (dono único de): notação e conversão, geração de paleta, gamut, medição de par renderizado, tokens semânticos, variantes de aparência (dark / `prefers-contrast` / forced-colors).

Estrutura:

```
foundations/color/
├── SKILL.md                    ← 3–4 princípios, Quick Reference, Common Mistakes
├── references/
│   ├── oklch-and-conversion.md
│   ├── palette-generation.md   ← algoritmo, delta 0.4, chroma como % do máximo
│   ├── contrast-measurement.md ← APCA + WCAG 2, "report don't repaint"
│   ├── gamut-and-p3.md
│   ├── semantic-tokens.md      ← uma cor um significado (±15°), tokens por papel
│   └── appearance-variants.md  ← dark, prefers-contrast (+0.15 L), forced-colors
└── review-output.md
```

Fronteira com `accessibility`: **a11y decide quando contraste é exigido e se o par falha; color mede o par renderizado e muda as cores.**

### 7.2 `foundations/writing` (ou `content/writing`) — **prioridade alta**

Não sobrepõe `behavior/copy` (que é marketing). Cobre: voz e tom por superfície, rótulos de botão, texto de link, mensagens de erro, empty states, labels de settings, placeholders, capitalização, vocabulário de fluxo, restrições de i18n na escrita.

Cabe em um `SKILL.md` de ~120 linhas + `review-output.md`. É a skill de melhor razão valor/esforço da lista.

**Ação complementar:** estreitar os triggers de `behavior/copy` para não capturar pedidos de copy de interface, e adicionar um handoff explícito.

### 7.3 `systems/layout` — **prioridade média-alta**

Extrair `refactoring` §2 e §7 + partes de `advanced-patterns.md` e criar dono único: agrupamento (regra do 2×), alinhamento a bordas compartilhadas, propriedades lógicas e RTL espacial, folga entre alvos (12/24px, aditivo aos hit areas), progressive disclosure com pista visível, full-bleed vs safe areas, breakpoints a partir do conteúdo, container queries, crescimento de string e clipping, **escala de z-index/elevação** (que hoje não existe em lugar nenhum).

### 7.4 `review/interface-review` — **prioridade média**

Review de diff/PR. É a lacuna estrutural mais limpa e a que mais diferencia um plugin de UI hoje, porque conecta as skills ao workflow real (PR).

Requer o §8.1 e §8.2 do backlog abaixo como pré-requisito — sem severidade compartilhada e formato de saída, não há o que uma skill de diff possa entregar.

### 7.5 Promover `_coordinator` a `ui-review` (orquestrador de verdade)

Não é skill nova: é dar ao `_coordinator` o que falta — modos `quick`/`full` com cap, recon de convenções do projeto, tabela de cobertura, tratamento de skill indisponível, arbitragem de conflito, "Considered but Rejected", read-only por padrão, veredito.

---

## 8. Backlog priorizado

Esforço: **P** = pequeno (< 1h) · **M** = médio (algumas horas) · **G** = grande (dias)

### P0 — correção e integridade

| # | Ação | Onde | Esforço |
|---|---|---|---|
| 1 | Corrigir os dois ratios de contraste errados | `foundations/accessibility` tabela Quick Check | P |
| 2 | Corrigir a aritmética do frequency gate (30s, não 3min) | `animation-motion` Common Mistake 1 | P |
| 3 | Remover a alegação de "mobile accessibility standard" para 40×40 e ancorar em WCAG 2.5.8 | `visual-polish` §13 | P |
| 4 | Corrigir/remover o código quebrado de `web-standards` (`next-usp`, `priority` em `<img>`, `onKeyDown` em `<button>` nativo, `navigator.language` em render, `-webkit-overflow-scrolling`, UA sniffing) | `foundations/web-standards` | M |
| 5 | Corrigir os padrões de a11y quebrados (Dropdown sem foco, `aria-selected` em menuitem, Modal sem `inert`/scroll lock, assertion Jest sem matcher) | `foundations/accessibility` | M |
| 6 | Substituir CSS inválido (`line-height: 1.1-1.25`, `.bar-gap`) por valores reais | `typography`, `data-visualization.md` | P |
| 7 | Consertar os 8 handoffs quebrados de frontmatter | 8 skills | P |

### P1 — governança (é isso que destrava o resto)

| # | Ação | Detalhe | Esforço |
|---|---|---|---|
| 8 | Criar `docs/OWNERSHIP.md` com tabela "regra → skill dona" | Espelhar o modelo do `AGENTS.md` do Jakub, incluindo a prosa que resolve fronteiras ambíguas | M |
| 9 | Resolver as 12 contradições de valor da §5.1 | Uma decisão por linha, aplicada em todos os arquivos | M |
| 10 | Unificar em **uma** escala de severidade | Sugestão: HIGH/MEDIUM/LOW + escalation triggers. Aposentar as outras três | M |
| 11 | Criar `review-output.md` por skill + seção `## Reporting` de 2 linhas no fim de cada `SKILL.md` | Começar pelas 4 de `foundations` | M |
| 12 | Adicionar exigência de evidência `path/to/file:line` + Before/After/Why em todos os formatos de saída | Junto com a regra anti-formato "nunca linhas separadas Before:/After:" | P |
| 13 | Tornar review read-only por padrão | Remover "evaluate **and improve**" de `heuristics` e "reviewing **or creating**" de `cro` | P |
| 14 | Adicionar seção "Considered but Rejected" ao formato consolidado | 1–3 em quick, 2–5 em full | P |
| 15 | Adicionar veredito Block / Needs changes / Approve e aposentar o score 0–10 sem rubrica | O score aparece com texto idêntico em 5 skills e nunca teve rubrica | P |
| 16 | Fazer os 12 especialistas referenciarem o `_coordinator` (e vice-versa) | Hoje a ligação é unidirecional e silenciosa | P |

### P2 — estrutura

| # | Ação | Detalhe | Esforço |
|---|---|---|---|
| 17 | Linkar os 14 arquivos de referência órfãos, ou movê-los, ou deletá-los | Prioridade: `microinteractions/case-studies.md` e `heuristics/audit-template.md` | M |
| 18 | Quebrar `web-standards` (1.195 linhas) e `accessibility` (985) em `SKILL.md` curto + `references/` | Adotar a regra: princípio enuncia, reference dá a receita, nenhum repete o outro | G |
| 19 | Mover `wcag-checklist.md` para dentro de `foundations/accessibility` como ledger de conformidade; deletar `accessibility-depth.md` e a seção de a11y de `krug-principles.md` | Elimina 3 das 5 vozes de a11y | M |
| 20 | Adicionar números de SC do WCAG às regras de `foundations/accessibility` | Sem isso nenhuma finding vira relatório de conformidade | M |
| 21 | Migrar de WCAG 2.1 para 2.2 | 2.4.11, 2.4.13, 2.5.7, **2.5.8**, 3.2.6, 3.3.7, 3.3.8 | M |
| 22 | Adicionar listas `Triggers on ...` ao frontmatter das 4 skills de `foundations` | Hoje só as adaptadas do wondelai têm palavras-chave densas | P |
| 23 | Alinhar o README com a realidade | Ele afirma "framework-agnostic" e "rather than boilerplate code"; ambos são falsos (React/Framer/Next/Tailwind em toda parte). Ou mudar a alegação, ou dar variantes não-React | P |

### P3 — skills novas

| # | Ação | Esforço |
|---|---|---|
| 24 | Criar `foundations/color` (§7.1) | G |
| 25 | Criar `foundations/writing` + estreitar triggers de `behavior/copy` (§7.2) | M |
| 26 | Criar `systems/layout` extraindo de `refactoring` (§7.3) | M |
| 27 | Promover `_coordinator` a orquestrador completo (§7.5) | M |
| 28 | Criar `review/interface-review` diff-scoped (§7.4) | G |

### P4 — cobertura pontual (adições baratas de alto valor)

| # | Adição | Skill destino |
|---|---|---|
| 29 | Regra de peso de traço de ícone (1.5px/400, 2px/600), um peso por conjunto | `visual-polish` |
| 30 | Um SVG com `currentColor`, estados por CSS; outline default, fill = ativo | `visual-polish` |
| 31 | Outline de imagem: preto/branco puro, nunca neutro tingido | `visual-polish` |
| 32 | `forced-colors` / Windows HCM — e a exceção que ela cria para "shadows over borders" | `accessibility` + `visual-polish` |
| 33 | Reduced motion como **substituição** (crossfade de opacidade), não kill-switch | `animation-motion` |
| 34 | `font-weight` vs `font-variation-settings`; `font-synthesis` como operação perigosa | `typography` |
| 35 | Line-height ≥1.4 para qualquer texto que quebra em 3+ linhas | `typography` |
| 36 | Regra bidi de parágrafo (1–2 linhas seguem a UI; 3+ seguem o próprio script) | `typography` |
| 37 | Escala de z-index / elevação | `systems/layout` (ou `refactoring` até lá) |
| 38 | Decisão Grid vs. Flexbox e primitivas de layout nomeadas | `systems/layout` |
| 39 | Regra do 2× para gap entre grupos vs. dentro do grupo | `systems/layout` |
| 40 | Fork "pergunte, não escolha" para zoom de input no iOS | `typography` |

---

## 9. O que **não** copiar do Jakub

Nem tudo lá é melhor.

1. **A estreiteza.** Ele não tem heurísticas de usabilidade, CRO, hábito, retenção nem microinterações no nível de detalhe que você tem. Seu `microinteractions/references/case-studies.md` sozinho é mais prescritivo sobre toast, loading e toggle do que qualquer coisa no repo dele. Não sacrifique isso em nome de simetria.

2. **A ausência de código de implementação.** Ele dá receitas CSS curtas; você dá componentes React completos. Para um agente que vai *construir*, os seus são mais úteis. O problema não é ter React — é o README alegar que não tem.

3. **`better-colors` sem parágrafo de handoff.** É a única skill dele sem essa seção, e é uma inconsistência, não uma escolha.

4. **`better-writing` sem arquivos de referência.** 115 linhas inline funciona para o escopo dele, mas se você for fundo em erro/empty state/i18n vai precisar de references.

5. **O cap de findings como número fixo.** 5/15 funciona para review de tela. Para um audit de heurísticas com 50 checks, o cap teria que ser por seção — o `audit-template.md` já resolve isso com slots estruturais (5 Top Issues, 3 Quick Wins).

---

## Anexo — inventário das 8 skills do Jakub

| Skill | Linhas | References | Papel |
|---|---|---|---|
| `better-typography` | 136 | 6 + review-output | Renderização de texto, quebra, bidi |
| `better-colors` | 86 | 5 + review-output | OKLCH, paletas, gamut, medição de contraste |
| `better-layout` | 79 | 2 + review-output | Agrupamento, alinhamento, adaptatividade, RTL espacial |
| `better-writing` | 115 | 0 + review-output | Copy de interface |
| `better-ui` | 108 | 6 + review-output | Polimento: superfícies, ícones, movimento |
| `better-accessibility` | 101 | 6 + review-output | Semântica, teclado, ARIA, formulários, AT |
| `better-interface` | 187 | 0 | Orquestrador: modo, severidade, cap, formato, veredito |
| `interface-review` | 142 | 2 | Escopo de mudança, blast radius, classificação |

**Total: 4.160 linhas.** Distribuição tripla: plugin Claude Code (`interfaces`), `npx skills add jakubkrehel/skills`, e opencode via `opencode.json`.

---

*Fontes: leitura integral de `github.com/jakubkrehel/skills` @ main e de `plugins/ui-excellence` @ working tree.*
