import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Decision, Landing, OtherSession, Registration } from '../types'

// ── Constantes ──────────────────────────────────────────────────────────────

const PANE = 'decisoes'
const TOOL = 'registrar_decisao'
const TOOL_FULL = 'mcp__decisoes__registrar_decisao'
/** Uma sessão que não atualizou o cadastro nesse intervalo é tratada como encerrada */
const ALIVE_MS = 90_000
const HEARTBEAT_MS = 30_000
/** Cadastros mais velhos que isso somem da lista de outras sessões */
const STALE_MS = 14 * 24 * 60 * 60 * 1000
/** Onde procurar o CLI do Cmux, nesta ordem */
const CMUX_CANDIDATES = ['cmux', '/Applications/cmux.app/Contents/Resources/bin/cmux']

/** Linhas do texto do agente que indicam uma decisão de quem usa a sessão */
const TEXT_MARKERS = /🔴|aguardo (o )?seu aval|preciso da sua decis[aã]o|depende de voc[eê] decidir/i

/** Como os textos chamam quem decide, com o artigo; a opção `dono` do plugin troca */
const DONO_PADRAO = 'o usuário'

/** "o usuário" → "O usuário", para o começo de frase */
const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

const instructions = (dono: string) => [
  `Decisões que esperam ${dono}. Quando surgir algo que só ${dono} pode decidir`,
  '(aprovar merge ou deploy, mudar escopo, aceitar ou adiar um achado de revisão,',
  'definir prazo, dar aval a uma seção ou proposta, escolher entre caminhos com custo',
  'ou risco diferentes), chame a ferramenta mcp__decisoes__registrar_decisao em vez de',
  'só perguntar no texto. Dê opções curtas e mutuamente exclusivas (até 9), indique a',
  'recomendada e diga em `bloqueia` se você precisa parar até a resposta. Depois de',
  'registrar, siga com o que não depende da decisão ou pouse; não repita a pergunta',
  'no texto. Não registre o que você mesmo pode decidir com segurança. As respostas',
  'chegam depois numa mensagem do plugin decisoes.',
].join(' ')

// ── Estado (redesenha quem lê) ──────────────────────────────────────────────

const decisions = atom({ plugin: 'decisoes', key: 'decisions' } as const, [] as Decision[])
const others = atom({ plugin: 'decisoes', key: 'others' } as const, [] as OtherSession[])
const nowAtom = atom({ plugin: 'decisoes', key: 'now' } as const, 0)
const landing = atom({ plugin: 'decisoes', key: 'landing' } as const, null as Landing | null)

const LANDED = /POUSO (DE EMERGÊNCIA )?CONCLUÍDO/

const landingText = (dono: string) => ({
  organizado: [
    `Pouso organizado: ${dono} vai fechar a máquina em breve (alguns minutos).`,
    'Não comece frente nova. Termine o passo atual até um ponto consistente, sem deixar arquivo pela metade.',
    'Depois: (1) guarde o trabalho em andamento do jeito que este projeto prefere (commit local de WIP ou stash nomeado; sem push forçado);',
    '(2) encerre os processos e monitores que você iniciou, ou diga quais continuam;',
    '(3) registre o estado onde este projeto guarda isso (issue, nota de sessão ou .planning): o que foi feito, o que falta, próximos passos e decisões pendentes, e gere um prompt de retomada;',
    "(4) responda com um resumo de até 5 linhas terminando em 'POUSO CONCLUÍDO'.",
  ].join(' '),
  emergencia: [
    `Pouso de emergência: ${dono} vai fechar a máquina agora (1 a 2 minutos).`,
    'Pare assim que for seguro, sem deixar arquivo corrompido. Não rode testes, builds nem nada demorado.',
    'Faça só: guarde o trabalho em andamento (commit local de WIP ou stash nomeado, sem push);',
    'escreva em até 5 linhas onde parou e o próximo passo, num arquivo ou comentário de retomada do projeto;',
    "responda terminando em 'POUSO DE EMERGÊNCIA CONCLUÍDO'.",
  ].join(' '),
})

type $T = EngineInterface

// ── Utilidades ──────────────────────────────────────────────────────────────

const isPending = (d: Decision) => d.estado === 'pendente' || d.estado === 'adiada'

/** Pendentes primeiro, adiadas depois, cada grupo pela ordem de chegada */
const queue = (list: Decision[]) =>
  list
    .filter(isPending)
    .sort((a, b) => (a.estado === b.estado ? a.seq - b.seq : a.estado === 'pendente' ? -1 : 1))

function ago(ms: number): string {
  const m = Math.max(0, Math.floor(ms / 60_000))
  if (m < 1) return 'agora'
  if (m < 60) return `${m}min`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h${String(m % 60).padStart(2, '0')}`
  return `${Math.floor(h / 24)}d`
}

const shorten = (text: string, max: number) =>
  text.length <= max ? text : text.slice(0, max - 1).trimEnd() + '…'

const shellQuote = (s: string) => `'${s.replace(/'/g, `'\\''`)}'`

/** Tira marcadores e ênfase markdown de uma linha detectada no texto */
const cleanLine = (line: string) =>
  line
    .replace(/🔴/g, '')
    .replace(/[*_`]+/g, '')
    .replace(/^[\s\-•>#]+/, '')
    .trim()

/** O que `cmux tree --all --json --id-format both` diz de uma aba: onde ela está e como se chama */
type Located = { windowId?: string; workspaceId: string; workspaceTitle?: string; surfaceRef?: string; surfaceTitle?: string }

const upper = (v: unknown) => (typeof v === 'string' ? v.toUpperCase() : '')

/** Título de aba sem o ✳ que o Claude Code põe no título do terminal */
const tidyTitle = (t: unknown) => (typeof t === 'string' ? t.replace(/^\s*✳\s*/, '').trim() || undefined : undefined)

/** Acha a aba `surfaceId` (UUID) na árvore de todas as janelas do Cmux */
function locate(tree: unknown, surfaceId: string): Located | undefined {
  const want = surfaceId.toUpperCase()
  const t = tree as { windows?: { id?: string; workspaces?: Record<string, unknown>[] }[] } | undefined
  for (const win of t?.windows ?? []) {
    for (const ws of win.workspaces ?? []) {
      const panes = (ws.panes as { surfaces?: Record<string, unknown>[] }[] | undefined) ?? []
      for (const pane of panes) {
        for (const sf of pane.surfaces ?? []) {
          if (upper(sf.id) === want) {
            return {
              windowId: win.id,
              workspaceId: String(ws.id),
              workspaceTitle: tidyTitle(ws.title),
              surfaceRef: typeof sf.ref === 'string' ? sf.ref : undefined,
              surfaceTitle: tidyTitle(sf.title),
            }
          }
        }
      }
    }
  }
  return undefined
}

/** O workspace `workspaceId` na árvore: a janela dele e o título */
function locateWorkspace(tree: unknown, workspaceId: string) {
  const want = workspaceId.toUpperCase()
  const t = tree as { windows?: { id?: string; workspaces?: Record<string, unknown>[] }[] } | undefined
  for (const win of t?.windows ?? []) {
    for (const ws of win.workspaces ?? []) {
      if (upper(ws.id) === want) return { windowId: win.id, title: tidyTitle(ws.title) }
    }
  }
  return undefined
}

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return undefined
  }
}

// ── O mod ───────────────────────────────────────────────────────────────────

// Valores do módulo: refeitos a cada recarga em session.start (o estado que importa fica em $.state e $.store)
let sessionId = ''
let cmuxPath: string | null | undefined // undefined: ainda não procurado; null: não achado
let registeredThisTurn = false
let turnRunning = false
let namesFetchedAt = 0
/** Quem decide, como os textos o chamam; vem da opção `dono` em cada carga */
let dono = DONO_PADRAO
let cachedNames: { workspaceName?: string; tabTitle?: string; windowId?: string } = {}

// ── Cmux ────────────────────────────────────────────────────────────────

async function cmux($: $T, args: string[]) {
  const candidates = cmuxPath ? [cmuxPath] : cmuxPath === null ? [] : CMUX_CANDIDATES
  for (const bin of candidates) {
    try {
      // CMUX_QUIET cala os avisos de alias que o CLI escreve em stderr
      const r = await $.process.run([bin, ...args], { timeoutMs: 10_000, env: { CMUX_QUIET: '1' } })
      if (r.exitCode === 127) continue
      cmuxPath = bin
      return r
    } catch {
      // binário não encontrado: tenta o próximo
    }
  }
  if (cmuxPath === undefined) cmuxPath = null
  return { exitCode: -1, stdout: '', stderr: 'cmux não encontrado' }
}

/** A árvore de todas as janelas; `list-workspaces` só mostra a janela de quem chama */
async function cmuxTree($: $T) {
  const r = await cmux($, ['tree', '--all', '--json', '--id-format', 'both'])
  return { exitCode: r.exitCode, tree: r.exitCode === 0 ? parseJson(r.stdout) : undefined }
}

async function fetchNames($: $T, surfaceId: string) {
  const { tree } = await cmuxTree($)
  const here = tree ? locate(tree, surfaceId) : undefined
  if (here) cachedNames = { workspaceName: here.workspaceTitle, tabTitle: here.surfaceTitle, windowId: here.windowId }
}

// ── Persistência ────────────────────────────────────────────────────────

async function loadDecisions($: $T) {
  const saved = (await $.store.get(`dec:${sessionId}`)) as Decision[] | undefined
  await update($, decisions, () => (Array.isArray(saved) ? saved : []))
}

async function saveDecisions($: $T, fn: (list: Decision[]) => Decision[]) {
  await update($, decisions, fn)
  const list = await read($, decisions)
  // Enviadas há mais de um dia não precisam ficar guardadas
  const now = await $.clock.now()
  const kept = list.filter(d => d.estado !== 'enviada' || now - (d.respondidaEm ?? now) < 86_400_000)
  await $.store.set(`dec:${sessionId}`, kept)
  heartbeat($).catch(() => {})
}

/** Grava o cadastro desta sessão e relê o das outras */
async function heartbeat($: $T) {
  const id = await $.session.id()
  if (id !== sessionId) {
    // /clear ou retomada trocou o id: a sessão anterior fica marcada como encerrada
    if (sessionId) await markEnded($, sessionId)
    sessionId = id
    await loadDecisions($)
  }
  const now = await $.clock.now()
  const workspaceId = await $.env.get('CMUX_WORKSPACE_ID')
  const surfaceId = await $.env.get('CMUX_SURFACE_ID')
  if (surfaceId && now - namesFetchedAt > 2 * 60_000) {
    namesFetchedAt = now
    await fetchNames($, surfaceId)
  }
  const pend = queue(await read($, decisions))
  const reg: Registration = {
    sessionId,
    cwd: await $.session.cwd(),
    workspaceId,
    surfaceId,
    windowId: cachedNames.windowId,
    workspaceName: cachedNames.workspaceName,
    tabTitle: cachedNames.tabTitle,
    pending: pend.length,
    oldestPendingAt: pend.length ? Math.min(...pend.map(d => d.criadaEm)) : undefined,
    lastSeen: now,
  }
  await $.store.set(`reg:${sessionId}`, reg)

  const list: OtherSession[] = []
  for (const key of await $.store.keys()) {
    if (!key.startsWith('reg:') || key === `reg:${sessionId}`) continue
    const other = (await $.store.get(key)) as Registration | undefined
    if (!other) continue
    if (now - other.lastSeen > STALE_MS) {
      await $.store.delete(key)
      continue
    }
    if (other.pending <= 0) continue
    const ws = other.workspaceName ?? 'sessão'
    const tab = other.tabTitle ?? other.sessionId.slice(0, 8)
    list.push({
      sessionId: other.sessionId,
      label: `${shorten(ws, 22)} › ${shorten(tab, 28)}`,
      pending: other.pending,
      isAlive: !other.ended && now - other.lastSeen < ALIVE_MS,
    })
  }
  list.sort((a, b) => b.pending - a.pending)
  await update($, others, () => list)
  await update($, nowAtom, () => now)
}

async function markEnded($: $T, id: string) {
  const reg = (await $.store.get(`reg:${id}`)) as Registration | undefined
  if (reg) await $.store.set(`reg:${id}`, { ...reg, ended: true, lastSeen: await $.clock.now() })
}

// ── Decisões ────────────────────────────────────────────────────────────

async function addDecision($: $T, d: Omit<Decision, 'id' | 'seq' | 'criadaEm' | 'estado'>) {
  const now = await $.clock.now()
  let id = ''
  await saveDecisions($, list => {
    const seq = list.reduce((m, x) => Math.max(m, x.seq), 0) + 1
    id = `D-${seq}`
    return [...list, { ...d, id, seq, criadaEm: now, estado: 'pendente' }]
  })
  $.ui.toast(`⚑ Nova decisão ${id}: ${shorten(d.pergunta, 60)}`)
  return id
}

async function answer($: $T, id: string, resposta: string) {
  if (!resposta) return
  const now = await $.clock.now()
  await saveDecisions($, list =>
    list.map(d => (d.id === id ? { ...d, estado: 'respondida', resposta, respondidaEm: now } : d)),
  )
  // Respondida a última que estava na fila (adiadas não contam), envia o lote
  const rest = (await read($, decisions)).filter(d => d.estado === 'pendente')
  if (rest.length === 0) await sendBatch($)
}

async function postpone($: $T, id: string) {
  await saveDecisions($, list => list.map(d => (d.id === id ? { ...d, estado: 'adiada' } : d)))
}

async function sendBatch($: $T) {
  const answered = (await read($, decisions)).filter(d => d.estado === 'respondida')
  if (answered.length === 0) return
  const lines = answered.map(d => `- ${d.id} — ${d.pergunta}\n  Resposta: ${d.resposta}`)
  const text = [
    `Respostas às decisões (${answered.length}):`,
    ...lines,
    '',
    'Siga a partir daqui com base nessas respostas.',
  ].join('\n')
  // Entra como turno próprio assim que a sessão estiver ociosa
  $.prompt.submit({ text }).catch(() => $.ui.toast('Não consegui enviar as decisões ao Claude.'))
  const ids = new Set(answered.map(d => d.id))
  await saveDecisions($, list => list.map(d => (ids.has(d.id) ? { ...d, estado: 'enviada' } : d)))
  $.ui.toast(`✓ ${answered.length} ${answered.length === 1 ? 'decisão enviada' : 'decisões enviadas'} ao Claude`)
  await $.ui.close({ id: PANE })
}

async function openPane($: $T) {
  await $.ui.open({ id: PANE, title: 'Decisões', focus: true, closeOnEscape: true })
}

// ── Navegação para outra sessão ─────────────────────────────────────────

async function requestLanding($: $T, kind: Landing['kind']) {
  const text = landingText(dono)[kind]
  let injected = false
  if (turnRunning) {
    // Entra no turno em curso: o modelo lê no próximo passo, sem interromper a ferramenta que está rodando
    try {
      const r = await $.session.append({ message: { type: 'user', content: [{ type: 'text', text }] } })
      injected = !('deny' in r && r.deny)
    } catch {
      injected = false
    }
  }
  // Sessão parada, ou a injeção falhou: vira um turno próprio assim que a sessão ficar ociosa
  if (!injected) $.prompt.submit({ text }).catch(() => $.ui.toast('Não consegui pedir o pouso ao Claude.'))
  await update($, landing, () => ({ kind, startedAt: Date.now() }))
  $.ui.toast(kind === 'emergencia' ? '⚠ Pouso de emergência pedido' : '🛬 Pouso organizado pedido')
}

async function goTo($: $T, targetId: string, label: string) {
  const reg = (await $.store.get(`reg:${targetId}`)) as Registration | undefined
  if (!reg) return $.ui.toast('Essa sessão não está mais no cadastro.')
  const resume = `claude --resume ${reg.sessionId}`
  const fallback = async (why: string) => {
    const full = `cd ${shellQuote(reg.cwd)} && ${resume}`
    const copied = await $.ui.copy({ text: full })
    $.ui.toast(`${why} ${copied.isCopied ? 'Copiei o comando para retomar.' : `Retome com: ${full}`}`, { timeoutMs: 8000 })
  }
  if (!reg.workspaceId || !reg.surfaceId) return fallback('Essa sessão não foi aberta pelo Cmux.')

  const { exitCode, tree } = await cmuxTree($)
  if (exitCode === -1) return fallback('Não achei o CLI do Cmux.')
  if (!tree) return fallback('O Cmux não respondeu à consulta das abas.')

  const now = await $.clock.now()
  const isAlive = !reg.ended && now - reg.lastSeen < ALIVE_MS
  const tab = locate(tree, reg.surfaceId)

  const focus = async (workspaceId: string, panel: string, windowId?: string) => {
    const win = windowId ? ['--window', windowId] : []
    await cmux($, ['select-workspace', '--workspace', workspaceId, ...win])
    await cmux($, ['focus-panel', '--panel', panel, '--workspace', workspaceId, ...win])
  }

  if (isAlive && tab) return focus(tab.workspaceId, reg.surfaceId, tab.windowId)

  const ws = locateWorkspace(tree, reg.workspaceId)
  if (!ws) return fallback('O workspace dessa sessão não existe mais no Cmux.')
  const where = ws.title ?? reg.workspaceName ?? 'o workspace de origem'
  const question = tab
    ? `A sessão de ${label} foi encerrada naquela aba. Retomar numa aba nova de ${where}?`
    : `${label} não está mais aberta no Cmux. Retomar a sessão numa aba nova de ${where}?`
  let choice = 'Cancelar'
  try {
    choice = await $.ui.ask(question, ['Abrir em aba nova', 'Cancelar'])
  } catch {
    return
  }
  if (choice !== 'Abrir em aba nova') return

  const win = ws.windowId ? ['--window', ws.windowId] : []
  const created = await cmux($, [
    'new-surface',
    '--workspace',
    reg.workspaceId,
    ...win,
    '--working-directory',
    reg.cwd,
    '--command',
    resume,
    '--focus',
    'true',
  ])
  // O Cmux responde "OK surface:33 pane:9 workspace:9"
  const fresh = created.stdout.match(/surface:\d+/)?.[0]
  if (created.exitCode !== 0 || !fresh) return fallback('O Cmux não abriu a aba nova.')
  if (reg.tabTitle) {
    await cmux($, ['rename-tab', '--workspace', reg.workspaceId, ...win, '--surface', fresh, '--title', reg.tabTitle])
  }
  await focus(reg.workspaceId, fresh, ws.windowId)
}

// ── Ciclo de vida ───────────────────────────────────────────────────────

export const register: Register = (on, options) => {
  dono = typeof options.dono === 'string' && options.dono.trim() ? options.dono.trim() : DONO_PADRAO

  // ── Ciclo de vida ───────────────────────────────────────────────────────

  on('session.start', async ($, e, next) => {
    sessionId = await $.session.id()
    await loadDecisions($)
    await $.tool.register({
      name: TOOL,
      description:
        `Registra uma decisão que só ${dono} pode tomar, sem travar a sessão. A resposta vem depois, por botões, ` +
        'e chega como mensagem do plugin decisoes. Use para merge, deploy, escopo, prazo, aval, ' +
        'ou escolha entre caminhos de custo ou risco diferentes. Não use para o que você pode decidir sozinho.',
      inputSchema: {
        type: 'object',
        properties: {
          pergunta: { type: 'string', description: 'A pergunta, curta e direta' },
          contexto: { type: 'string', description: 'Até 2 frases com o que ele precisa saber para decidir' },
          opcoes: {
            type: 'array',
            items: { type: 'string' },
            maxItems: 9,
            description: 'Opções curtas e mutuamente exclusivas',
          },
          recomendada: { type: 'integer', minimum: 1, maximum: 9, description: 'Número da opção recomendada' },
          bloqueia: { type: 'boolean', description: 'true se você vai parar até a resposta' },
        },
        required: ['pergunta'],
      },
    })
    await $.command.register({ name: 'decisoes', description: 'Abre as decisões pendentes desta sessão', immediate: true })
    $.clock.every(HEARTBEAT_MS, () => {
      heartbeat($).catch(() => {})
    })
    await heartbeat($)
    return next(e)
  })

  on('classic.SessionStart', { source: ['clear', 'resume', 'fork'] }, async ($, e, next) => {
    await heartbeat($)
    return next(e)
  })

  on('session.end', async ($, e, next) => {
    if (sessionId) await markEnded($, sessionId)
    return next(e)
  })

  on('command.run', { command: 'decisoes' }, async $ => {
    await openPane($)
    return {}
  })

  // ── Instrução para o agente ─────────────────────────────────────────────

  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    return {
      ...composed,
      sections: [...composed.sections, { id: 'decisoes:instrucoes', text: instructions(dono), scope: 'session' as const }],
    }
  })

  // ── Captura ─────────────────────────────────────────────────────────────

  on('tool.call', { tool: TOOL_FULL }, async ($, e) => {
    const input = e as unknown as Record<string, unknown>
    const pergunta = typeof input.pergunta === 'string' ? input.pergunta.trim() : ''
    if (!pergunta) return { deny: 'Informe a pergunta.' }
    const opcoes = Array.isArray(input.opcoes)
      ? input.opcoes.filter((o): o is string => typeof o === 'string' && o.trim().length > 0).slice(0, 9)
      : []
    const rec = typeof input.recomendada === 'number' && input.recomendada >= 1 && input.recomendada <= opcoes.length
    registeredThisTurn = true
    const id = await addDecision($, {
      pergunta,
      contexto: typeof input.contexto === 'string' && input.contexto.trim() ? input.contexto.trim() : undefined,
      opcoes,
      recomendada: rec ? (input.recomendada as number) : undefined,
      bloqueia: input.bloqueia === true,
      origem: 'ferramenta',
    })
    return {
      result:
        `Registrada como ${id}. ${capitalize(dono)} decide quando voltar e a resposta chega numa mensagem do plugin decisoes. ` +
        'Siga com o que não depende disso ou pouse; não repita a pergunta no texto.',
    }
  })

  on('turn.start', ($, e, next) => {
    registeredThisTurn = false
    turnRunning = true
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    if (e.agentId === undefined) turnRunning = false
    if (e.agentId === undefined && LANDED.test(e.answer) && (await read($, landing))) {
      await update($, landing, () => null)
      $.ui.toast('✓ Pouso concluído. Pode fechar a máquina.', { timeoutMs: 15_000 })
    }
    if (e.agentId === undefined && !e.isAborted && !registeredThisTurn) {
      const lines = e.answer
        .split('\n')
        .filter(l => TEXT_MARKERS.test(l))
        .map(cleanLine)
        .filter(l => l.length > 3)
        .slice(0, 3)
      const existing = new Set((await read($, decisions)).filter(isPending).map(d => d.pergunta))
      for (const pergunta of lines) {
        if (existing.has(pergunta)) continue
        await addDecision($, { pergunta, opcoes: [], bloqueia: true, origem: 'texto' })
      }
    }
    registeredThisTurn = false
    return next(e)
  })

  // ── Faixa acima do prompt (sempre visível) ──────────────────────────────

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const { Box, Text, Button } = $.ui.resolve(e)
    const list = await read($, decisions)
    const outras = await read($, others)
    const now = (await read($, nowAtom)) || Date.now()
    const pend = queue(list)
    const answered = list.filter(d => d.estado === 'respondida')
    const isBlocked = pend.some(d => d.bloqueia && d.estado === 'pendente')
    const oldest = pend.length ? Math.min(...pend.map(d => d.criadaEm)) : 0
    const pouso = await read($, landing)
    const below = await next(e)

    return (
      <Box flexDirection="column">
        <Box flexDirection="row" columnGap={1}>
          {pend.length > 0 ? (
            <Text>
              <Text color="warning" bold>⚑ {pend.length} {pend.length === 1 ? 'decisão' : 'decisões'}</Text>
              {' nesta sessão · mais antiga há '}
              {ago(now - oldest)}
              {isBlocked ? ' · ⏸ sessão parada esperando você' : ''}
            </Text>
          ) : (
            <Text dimColor>⚑ nenhuma decisão pendente nesta sessão</Text>
          )}
          {pend.length > 0 && <Button key="abrir" label="decidir" variant="primary" onPress={() => openPane($)} />}
          {answered.length > 0 && (
            <Text dimColor>
              · {answered.length} {answered.length === 1 ? 'respondida' : 'respondidas'} aguardando envio
            </Text>
          )}
          {answered.length > 0 && <Button key="enviar" label="enviar agora" onPress={() => sendBatch($)} />}
          <Text dimColor>│</Text>
          {pouso ? (
            <Text color="warning">
              {pouso.kind === 'emergencia' ? '⚠ pouso de emergência' : '🛬 pouso organizado'} em andamento · há{' '}
              {ago(now - pouso.startedAt)}
            </Text>
          ) : (
            <Box flexDirection="row" columnGap={2}>
              <Button key="pouso" plain dimColor label="🛬 pousar" onPress={() => requestLanding($, 'organizado')} />
              <Button key="pouso-emergencia" plain dimColor label="⚠ pouso de emergência" onPress={() => requestLanding($, 'emergencia')} />
            </Box>
          )}
        </Box>
        {outras.length > 0 && (
          <Box flexDirection="row" columnGap={2}>
            <Text dimColor>outras ›</Text>
            {outras.slice(0, 4).map(o => (
              <Button
                key={`outra-${o.sessionId}`}
                plain
                dimColor
                label={`${o.label} (${o.pending})${o.isAlive ? '' : ' ○'}`}
                onPress={() => goTo($, o.sessionId, o.label)}
              />
            ))}
          </Box>
        )}
        {below ?? null}
      </Box>
    )
  })

  // ── Painel de decisão ───────────────────────────────────────────────────

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e, next) => {
    // O painel é para o terminal e o app desktop; outras superfícies ficam com o desenho do engine
    if (e.surface !== 'terminal' && e.surface !== 'desktop') return next(e)
    const { Box, Text, Button, Input } = $.ui.resolve(e)
    const list = await read($, decisions)
    const now = (await read($, nowAtom)) || Date.now()
    const pend = queue(list)
    const answered = list.filter(d => d.estado === 'respondida')
    const close = () => $.ui.close({ id: PANE })

    if (pend.length === 0) {
      return (
        <Box flexDirection="column">
          <Text>{answered.length > 0 ? `Tudo respondido (${answered.length}).` : 'Nenhuma decisão pendente nesta sessão.'}</Text>
          <Box flexDirection="row" columnGap={2}>
            {answered.length > 0 && (
              <Button key="enviar" label="Enviar ao Claude" variant="primary" autoFocus onPress={() => sendBatch($)} />
            )}
            <Button key="fechar" label="Fechar" role="dismiss" onPress={close} />
          </Box>
        </Box>
      )
    }

    const d = pend[0]
    if (!d) return next(e)
    const width = Math.max(20, e.props.bodyColumns - 2)
    return (
      <Box flexDirection="column">
        <Text bold>
          Decisão 1 de {pend.length} · {d.id} · há {ago(now - d.criadaEm)}
          {d.estado === 'adiada' ? ' · adiada' : ''}
          {d.bloqueia ? ' · ⏸ sessão parada' : ''}
        </Text>
        <Text> </Text>
        <Box width={width}>
          <Text wrap="wrap">{d.pergunta}</Text>
        </Box>
        {d.contexto && (
          <Box width={width}>
            <Text dimColor wrap="wrap">{d.contexto}</Text>
          </Box>
        )}
        <Text> </Text>
        {d.opcoes.map((opt, i) => (
          <Button
            key={`opt-${d.id}-${i + 1}`}
            plain
            hotkey={String(i + 1)}
            label={`${opt}${d.recomendada === i + 1 ? '   ★ recomendada' : ''}`}
            onPress={() => answer($, d.id, `[${i + 1}] ${opt}`)}
          />
        ))}
        <Input
          key={`outra-${d.id}`}
          label={d.opcoes.length > 0 ? 'Outra resposta' : 'Resposta'}
          placeholder="digite e tecle Enter"
          value=""
          submitLabel="responder"
          autoFocus={d.opcoes.length === 0 ? true : undefined}
          onSubmit={(v: string) => answer($, d.id, v.trim())}
        />
        <Text> </Text>
        <Box flexDirection="row" columnGap={3}>
          <Button key="adiar" plain hotkey="a" label="adiar" onPress={() => postpone($, d.id)} />
          {answered.length > 0 && (
            <Button key="enviar" plain hotkey="e" label={`enviar ${answered.length} já respondida(s)`} onPress={() => sendBatch($)} />
          )}
          <Button key="fechar" plain hotkey="f" label="fechar" onPress={close} />
        </Box>
        <Text dimColor>clique ou tecle o número · Tab até a resposta livre · Esc fecha</Text>
      </Box>
    )
  })
}
