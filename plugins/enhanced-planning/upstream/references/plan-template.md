# Plan Template — Secoes Obrigatorias

Template markdown que o agente injeta no plano. Todas as secoes abaixo sao obrigatorias.

---

## Template Completo

```markdown
## Contexto

[Problema, resultado esperado, decisoes ja tomadas]

---

## Implementacao

### [Deliverable/PR 1]: [Titulo]

**Objetivo:** [1 frase]

**Slices:**
- [Slice 1] — [descricao]
- [Slice 2] — [descricao]

**Arquivos a criar/modificar:**
- `path/to/file.py` — [o que muda]

**Criterio de aceite:**
- [ ] [Criterio verificavel 1]
- [ ] [Criterio verificavel 2]

---

## Checkpoints Humanos

| Gate | Momento | Pergunta |
|---|---|---|
| Design | Antes de implementar | Escopo e abordagem corretos? |
| Mid-point | Apos PR-1 / 50% dos slices | Resultados parciais alinhados? Ajustar algo? |
| Final | Todos criterios atendidos | Posso marcar como concluido? |
| Desbloqueio | Ao desbloquear dependencia | Confirmar escopo do proximo passo? |
| Por PR | Ao completar cada PR | Criterios atendidos? Posso registrar e avancar? |

---

## Guardrails Nomeados (G-*)

Consultar [guardrail-catalog.md](guardrail-catalog.md) e selecionar guardrails ativos.

**Guardrails ativos neste plano:**
- G-[ID]: [descricao de como se aplica]
- G-[ID]: [descricao de como se aplica]

**Regra:** Ao completar cada slice, verificar que todos guardrails ativos foram respeitados.

---

## Registro de Riscos

| Risco | Severidade | Mitigacao | Owner | Status |
|---|---|---|---|---|
| [Risco 1] | Alta/Media/Baixa | [Como mitigar] | [Quem] | Aberto/Mitigado |

---

## Tabela de Progresso

| Slice | Data | Commit | Status | Notas |
|---|---|---|---|---|
| | | | | |

---

## Isonomia Documental

Tabela completa de arquivos que devem ser mantidos em sincronia.

| Arquivo | Referencia | Acao ao Implementar | Verificado |
|---|---|---|---|
| [path] | [o que referencia] | [acao] | [ ] |

**Regra de isonomia:** ao completar cada PR, atualizar TODOS os arquivos listados. Nao commitar codigo sem atualizar docs correspondentes.

---

## Revisao Codex (com meta-avaliacao)

Consultar [codex-review-protocol.md](codex-review-protocol.md) para protocolo completo.

**Ao completar cada PR:**
1. Verificar criterios de aceite 100%
2. Completar verificacao cruzada
3. Invocar `/codex:rescue --effort xhigh` para executar revisao (2 fases: exploracao independente + classificacao comparativa)
4. **Meta-avaliacao Claude** dos achados (CRITICO → fix obrigatorio; MEDIO → ajuste opcional; BAIXO → observacao)
5. Registrar resultado na Tabela de Progresso

---

## Decision Locks

Decisoes congeladas ANTES da implementacao. Mudanca exige checkpoint humano explicito.

| Decisao | Data | Implicacao Downstream |
|---|---|---|
| [Decisao 1] | [Data] | [O que quebra se mudar] |
| [Decisao 2] | [Data] | [O que quebra se mudar] |

**Regra:** Para desbloquear uma decisao, o agente DEVE usar AskUserQuestion explicando: (1) a decisao original, (2) por que precisa mudar, (3) impacto downstream.

---

## Protocolo de Conclusao de PR

**OBRIGATORIO ao completar cada PR — executar TODOS os passos antes de iniciar proximo PR:**

1. **Marcar checkboxes:** Riscar (`- [x]`) TODOS os criterios de aceite do PR concluido neste plano
2. **Tabela de Progresso:** Preencher colunas Data, Commit (hashes), Status (`completo`) e Notas
3. **CONTEXT.md da initiative:** Adicionar entrada no "Diario de Rodadas" com:
   - O que foi entregue (lista de arquivos/modulos)
   - Commits (hashes)
   - Decisoes de design emergentes (se houver)
   - Proximo passo
4. **Verificacao cruzada:** Atualizar docs listados na tabela de Isonomia Documental
5. **Verificar guardrails:** Confirmar que todos G-* ativos foram respeitados neste PR
6. Informar: "PR-N completo. Recomendo `/compact` antes de prosseguir."
7. Aguardar confirmacao do usuario.
8. Se sessao >100k tokens, invocar `fresh-context` antes de prosseguir.

> **Regra:** Nenhum PR esta "completo" ate que passos 1-5 estejam feitos. O agente NAO deve iniciar o proximo PR sem antes registrar o progresso do PR anterior.

---

## Protocolo Multi-Sessao

1. **Ao completar cada slice:** atualizar checkboxes + Tabela de Progresso
2. **Ao completar cada PR:** executar Protocolo de Conclusao de PR (acima) integralmente
3. **Ao iniciar nova sessao:** ler plano integralmente, consultar Tabela de Progresso, retomar do proximo slice pendente
4. **Ao encerrar sessao sem completar PR:** registrar ponto exato de parada + decisoes pendentes no CONTEXT.md

---

## Sequencia de Commits

| PR | Commits Esperados | Type | Scope |
|---|---|---|---|
| PR-1 | [lista] | [feat/test/docs/...] | [scope] |

---

## Verificacao Final

- [ ] Todos criterios de aceite marcados (`- [x]`) em todos os PRs
- [ ] Tabela de progresso completa (todos PRs com data, commit, status)
- [ ] Verificacao cruzada de docs completa (isonomia)
- [ ] CONTEXT.md atualizado com diario de rodadas para cada PR
- [ ] Guardrails G-* verificados e nenhum violado
- [ ] Revisao Codex executada para cada PR (ou justificativa de skip)
- [ ] Decision locks respeitados (nenhum desbloqueado sem checkpoint)
- [ ] Testes passando (`pytest -q`)
- [ ] Cobertura atende meta do milestone
- [ ] Nenhum arquivo modificado fora do escopo do plano
- [ ] Protocolo multi-sessao seguido (tabela de progresso consistente)
- [ ] Documentacao atualizada (Projeto.md, Roadmap.md, TODO.md se aplicavel)
```
