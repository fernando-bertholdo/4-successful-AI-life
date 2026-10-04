import { describe, expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const TOOL = 'mcp__decisoes__registrar_decisao'
const WS = 'AAAAAAAA-0000-0000-0000-000000000001'
const TAB = 'BBBBBBBB-0000-0000-0000-000000000002'
const OTHER_TAB = 'CCCCCCCC-0000-0000-0000-000000000003'
const NOW = 1_800_000_000_000

const START = { cwd: '/projetos/lab', surface: 'terminal', isInteractive: true } as const

const BAND = {
  plugin: 'decisoes',
  surface: 'terminal',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 8, bodyColumns: 100, scroll: { offset: 0, bodyRows: 8 }, view: {} },
} as const

const PANE = {
  plugin: 'decisoes',
  surface: 'terminal',
  component: 'Pane',
  requestId: 'decisoes',
  props: { title: 'Decisões', isFocused: true, bodyColumns: 80, placement: 'inline', scroll: { offset: 0, bodyRows: 20 }, view: {} },
} as const

/** A árvore no formato que `cmux tree --all --json --id-format both` devolveu no Mac */
const tree = (surfaces: { id: string; ref: string; title: string }[]) =>
  JSON.stringify({
    windows: [
      {
        id: 'WIN-1',
        ref: 'window:1',
        workspaces: [{ id: WS, ref: 'workspace:7', title: 'projeto-b', panes: [{ id: 'P1', ref: 'pane:7', surfaces }] }],
      },
    ],
  })

type World = {
  submitted: string[]
  appended: string[]
  runs: string[][]
  asked: string[]
  /** Respostas do Cmux por comando; a função recebe os argumentos */
  cmux: (args: string[]) => { exitCode: number; stdout: string }
  askAnswer: string
}

/** O mundo abaixo do plugin: sessão S1 numa aba do Cmux */
function world(on: On, store: Record<string, unknown> = {}): World {
  const w: World = {
    submitted: [],
    appended: [],
    runs: [],
    asked: [],
    cmux: () => ({ exitCode: 0, stdout: '[]' }),
    askAnswer: 'Cancelar',
  }
  mock.clock(on, { now: NOW })
  mock.store(on, store)
  mock.env(on, { CMUX_WORKSPACE_ID: WS, CMUX_SURFACE_ID: TAB })
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('session.id', () => ({ value: 'S1' }))
  on('session.cwd', () => ({ value: '/projetos/lab' }))
  on('tool.register', ($, e) => ({ value: { tool: `mcp__decisoes__${e.name}` } }))
  on('command.register', ($, e) => ({ value: { command: e.name } }))
  on('ui.toast', () => ({ value: undefined }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  on('ui.copy', () => ({ value: { isCopied: true } }))
  // $.ui.ask é uma chamada de AskUserQuestion por baixo
  on('tool.call', { tool: 'AskUserQuestion' }, ($, e) => {
    const questions = (e as unknown as { questions: { question: string; options: { label: string }[] }[] }).questions
    const q = questions[0]!
    w.asked.push(q.question)
    return { result: { questions, answers: { [q.question]: w.askAnswer } } as never }
  })
  on('prompt.submit', ($, e) => {
    w.submitted.push(e.text)
    return { text: e.text }
  })
  // O que o engine desenharia sozinho na faixa e no painel: nada
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)
    return Box({ children: [] })
  })
  on('turn.complete', ($, e) => ({ text: e.answer }))
  on('turn.start', ($, e) => e as never)
  on('session.append', { door: 'note' }, ($, e) => {
    w.appended.push(JSON.stringify(e))
    return { message: e.message, uuid: 'u1' } as never
  })
  on('process.run', ($, e) => {
    const args = e.argv.slice(1)
    w.runs.push(args)
    const r = w.cmux(args)
    return { value: { ...r, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  return w
}

describe('register', () => {
  test('uma decisão registrada aparece na faixa e a resposta vai ao Claude', async ($, on) => {
    const w = world(on)
    await $.session.start(START)

    await $.tool.call({
      tool: TOOL,
      pergunta: 'Mergear o #133 e fazer o deploy?',
      contexto: 'CI verde.',
      opcoes: ['Mergear e fazer o deploy', 'Só mergear', 'Segurar'],
      recomendada: 1,
      bloqueia: true,
    } as never)

    const band = await $.ui.mount(BAND)
    expect(await band.find({ type: 'Text', text: /1 decisão/ })).toBeDefined()
    expect(await band.find({ key: 'abrir' })).toBeDefined()

    const pane = await $.ui.mount(PANE)
    expect(await pane.find({ type: 'Text', text: /Mergear o #133/ })).toBeDefined()
    expect(await pane.find({ key: 'opt-D-1-1' })).toBeDefined()

    await pane.press({ key: 'opt-D-1-2' })
    expect(w.submitted).toHaveLength(1)
    expect(w.submitted[0]).toContain('D-1')
    expect(w.submitted[0]).toContain('[2] Só mergear')

    expect(await band.find({ type: 'Text', text: /nenhuma decisão pendente/ })).toBeDefined()
  })

  test('duas decisões acumulam e saem juntas quando a última é respondida', async ($, on) => {
    const w = world(on)
    await $.session.start(START)
    await $.tool.call({ tool: TOOL, pergunta: 'Primeira?', opcoes: ['A', 'B'] } as never)
    await $.tool.call({ tool: TOOL, pergunta: 'Segunda?', opcoes: ['C', 'D'] } as never)

    const pane = await $.ui.mount(PANE)
    await pane.press({ key: 'opt-D-1-1' })
    expect(w.submitted).toHaveLength(0)
    await pane.input({ key: 'outra-D-2', text: 'nenhuma das duas' })
    expect(w.submitted).toHaveLength(1)
    expect(w.submitted[0]).toContain('[1] A')
    expect(w.submitted[0]).toContain('nenhuma das duas')
  })

  test('uma linha com 🔴 no texto vira decisão de resposta livre', async ($, on) => {
    world(on)
    await $.session.start(START)
    await $.turn.complete({
      answer: 'Feito.\n\n🔴 Aguardo seu aval à Seção 3 para seguir.',
      durationMs: 1000,
      isAborted: false,
      turnId: 't1',
      reason: 'answer',
    } as never)

    const pane = await $.ui.mount(PANE)
    expect(await pane.find({ type: 'Text', text: /Aguardo seu aval à Seção 3/ })).toBeDefined()
    expect(await pane.find({ key: 'outra-D-1' })).toBeDefined()
  })

  test('clicar numa sessão viva leva à aba dela no Cmux', async ($, on) => {
    const w = world(on, {
      'reg:S2': {
        sessionId: 'S2',
        cwd: '/projetos/b',
        workspaceId: WS,
        surfaceId: OTHER_TAB,
        workspaceName: 'projeto-b',
        tabTitle: 'clarify brainstorm',
        pending: 1,
        lastSeen: NOW,
      },
    })
    w.cmux = args =>
      args[0] === 'tree'
        ? { exitCode: 0, stdout: tree([{ id: OTHER_TAB, ref: 'surface:23', title: '✳ clarify brainstorm' }]) }
        : { exitCode: 0, stdout: 'OK' }
    await $.session.start(START)

    const band = await $.ui.mount(BAND)
    expect(await band.find({ key: 'outra-S2' })).toBeDefined()
    await band.press({ key: 'outra-S2' })

    expect(w.runs).toContainEqual(['select-workspace', '--workspace', WS, '--window', 'WIN-1'])
    expect(w.runs).toContainEqual(['focus-panel', '--panel', OTHER_TAB, '--workspace', WS, '--window', 'WIN-1'])
    expect(w.asked).toHaveLength(0)
  })

  test('aba fechada: pergunta e retoma a sessão numa aba nova do mesmo workspace', async ($, on) => {
    const w = world(on, {
      'reg:S2': {
        sessionId: 'S2',
        cwd: '/projetos/b',
        workspaceId: WS,
        surfaceId: OTHER_TAB,
        workspaceName: 'projeto-b',
        tabTitle: 'clarify brainstorm',
        pending: 1,
        lastSeen: NOW - 10 * 60_000,
        ended: true,
      },
    })
    w.askAnswer = 'Abrir em aba nova'
    w.cmux = args => {
      if (args[0] === 'new-surface') return { exitCode: 0, stdout: 'OK surface:9 pane:7 workspace:7' }
      if (args[0] === 'tree') return { exitCode: 0, stdout: tree([{ id: 'DDDDDDDD-0000-0000-0000-000000000004', ref: 'surface:1', title: 'outra' }]) }
      return { exitCode: 0, stdout: 'OK' }
    }
    await $.session.start(START)

    const band = await $.ui.mount(BAND)
    await band.press({ key: 'outra-S2' })

    expect(w.asked).toHaveLength(1)
    expect(w.runs).toContainEqual([
      'new-surface',
      '--workspace',
      WS,
      '--window',
      'WIN-1',
      '--working-directory',
      '/projetos/b',
      '--command',
      'claude --resume S2',
      '--focus',
      'true',
    ])
    expect(w.runs).toContainEqual(['rename-tab', '--workspace', WS, '--window', 'WIN-1', '--surface', 'surface:9', '--title', 'clarify brainstorm'])
    expect(w.runs).toContainEqual(['focus-panel', '--panel', 'surface:9', '--workspace', WS, '--window', 'WIN-1'])
  })

  test('pousar com a sessão parada vira um turno novo', async ($, on) => {
    const w = world(on)
    await $.session.start(START)
    const band = await $.ui.mount(BAND)
    await band.press({ key: 'pouso' })
    expect(w.submitted).toHaveLength(1)
    expect(w.submitted[0]).toContain('Pouso organizado')
    expect(await band.find({ type: 'Text', text: /pouso organizado em andamento/ })).toBeDefined()
    await $.turn.complete({ answer: 'Tudo guardado. POUSO CONCLUÍDO', durationMs: 1, isAborted: false, turnId: 't2', reason: 'answer' } as never)
    expect(await band.find({ key: 'pouso' })).toBeDefined()
  })

  test('pouso de emergência no meio de um turno: tenta entrar no turno e, sem isso, entra na fila', async ($, on) => {
    const w = world(on)
    await $.session.start(START)
    await $.turn.start({ turnId: 't1' } as never)
    const band = await $.ui.mount(BAND)
    await band.press({ key: 'pouso-emergencia' })
    // O kit de testes não implementa $.session.append; o mod cai na fila (prompt.submit)
    expect(w.appended.length + w.submitted.length).toBe(1)
    expect([...w.appended, ...w.submitted][0]).toContain('Pouso de emergência')
    expect(await band.find({ type: 'Text', text: /pouso de emergência em andamento/ })).toBeDefined()
  })
})
