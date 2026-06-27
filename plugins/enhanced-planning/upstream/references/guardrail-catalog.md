# Guardrail Catalog (G-*)

Guardrails nomeados para planos de alta complexidade. Cada guardrail tem nome, definicao, criterio de ativacao e exemplo.

## Niveis

### Semantico — Decisoes de negocio frozen antes de implementar

| ID | Nome | Definicao | Criterio de Ativacao | Exemplo |
|---|---|---|---|---|
| G-POLICY | Policy Lock | Congela regra de negocio antes de implementar. Impede reinterpretacao mid-flight. | Slice toca logica de classificacao, alerting ou KPI | "Regra de precificacao congelada: criterio X antes de implementar endpoint" |
| G-CANONICAL | Canonical Names | Congela nomenclaturas e aliases antes de refactor. Garante que renaming nao introduz ambiguidade. | Refactor de nomes publicos, constantes ou schemas | "Nomenclatura canonica: `STATUS_ACTIVE`, nao `active_status` nem `is_active`" |

### Teste — Baseline que deve existir antes de refatorar

| ID | Nome | Definicao | Criterio de Ativacao | Exemplo |
|---|---|---|---|---|
| G-FIXTURE | Fixture Registry | Congela fixtures com expectativas ANTES do refactor. Garante que golden set existe como rede de seguranca. | Refactor de logica de classificacao ou calculo | "15 fixtures com expected_output congelados antes do refactor" |
| G-CONTRACT | Contract Tests | Suite de testes de contrato cross-component que DEVE passar antes E depois de cada slice. | Mudanca toca 2+ componentes que compartilham contrato | "test_integration_contract.py — suite baseline de contrato" |

### Arquitetural — Padroes estruturais que garantem reprodutibilidade

| ID | Nome | Definicao | Criterio de Ativacao | Exemplo |
|---|---|---|---|---|
| G-CONTRACT-CATALOG | Central Catalog | Catalogo central de regras como single source of truth para logica dispersa. | Logica duplicada em 2+ arquivos com risco de drift | "rules_catalog.py como fonte unica de keywords e precedencia" |
| G-DETERMINISM | Deterministic Output | Output do componente deve ser deterministico dados os mesmos inputs. Proibe side-effects ocultos. | Componente alimenta alertas ou reports visiveis ao stakeholder | "process_items() retorna mesmo resultado para mesmo input independente de ordem" |
| G-BASELINE-PARITY | Baseline Parity (Infra Migration) | Em migracoes de ambiente (local→cloud, provedor→provedor), o baseline funcional do ambiente origem DEVE ser reproduzido no ambiente destino e validado por N dias de operacao paralela com comparacao de outputs. Diferenca nao-justificada = bloqueador de cutover. | Detour/milestone que migra execucao para outro ambiente ou provedor | "Cloud deployment vs local scheduler (cron/launchd/systemd): 7 dias de paralela com comparacao diaria de logs estruturados; divergencias nao-justificadas bloqueiam cutover" |

### Operacional — Guardrails em alerting/output para evitar erros humanos

| ID | Nome | Definicao | Criterio de Ativacao | Exemplo |
|---|---|---|---|---|
| G-TIEBREAK | Tiebreak Protocol | Define regra explicita de desempate quando classificacao e ambigua. Proibe silenciar ambiguidade. | Classificador pode produzir 2+ categorias igualmente validas | "Item com match em 2 categorias: usar precedencia definida no catalogo" |
| G-AMBIGUITY | Ambiguity Flag | Eventos ambiguos devem ser flagged, nao silenciados. Visibilidade > precisao falsa. | Output contabiliza categorias agregadas (totais, percentuais) | "Itens nao classificados devem aparecer como `UNCLASSIFIED` no report, nao ser omitidos" |
| G-NARRATIVE | Narrative Safety | Narrativa textual de alertas nao pode contradizer dados numericos. | Slice toca texto de alerta ou descricao visivel ao stakeholder | "Se label indica 'tipo A' mas 60% do volume e 'tipo B', narrativa deve refletir ambiguidade" |
| G-ISONOMIA | Cross-Component Parity | Classificadores independentes que consomem mesmos dados devem produzir resultados identicos. | 2+ classificadores operam sobre mesma fonte de dados | "classifier_v1 e classifier_v2 devem convergir para mesma categorizacao" |

---

## Como Usar no Plano

### Selecao

1. Ler a lista de guardrails acima
2. Para cada slice do plano, avaliar quais criterios de ativacao sao satisfeitos
3. Listar guardrails ativos no cabecalho do PR ou fase

### Formato no Plano

```markdown
**Guardrails ativos neste PR:**
- G-FIXTURE: golden set congelado com 15 fixtures antes de refactor
- G-CONTRACT: suite de contrato deve passar antes e apos cada slice
- G-ISONOMIA: convergencia entre classificadores validada por testes de contrato
```

### Verificacao

Ao completar cada slice, verificar:
- [ ] Todos guardrails ativos foram respeitados
- [ ] Nenhum guardrail foi violado ou silenciosamente ignorado
- [ ] Violacoes justificadas estao documentadas com rationale

---

## Criando Novos Guardrails

Ao identificar um novo padrao de risco recorrente:

1. Atribuir ID no formato `G-NOME` (UPPER_SNAKE_CASE)
2. Classificar no nivel correto (semantico, teste, arquitetural, operacional)
3. Definir criterio de ativacao claro e verificavel
4. Incluir exemplo concreto do projeto
5. Adicionar a este catalogo via PR
