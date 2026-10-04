export type DecisionState = 'pendente' | 'adiada' | 'respondida' | 'enviada'

export type Decision = {
  /** D-1, D-2… único dentro da sessão */
  id: string
  seq: number
  pergunta: string
  contexto?: string
  /** Opções de resposta (até 9); vazia quando a decisão veio do texto */
  opcoes: string[]
  /** Opção recomendada pelo agente, 1-based */
  recomendada?: number
  /** O agente parou esperando esta resposta */
  bloqueia: boolean
  origem: 'ferramenta' | 'texto'
  criadaEm: number
  estado: DecisionState
  resposta?: string
  respondidaEm?: number
}

/** Cadastro de uma sessão, gravado no armazenamento compartilhado */
export type Registration = {
  sessionId: string
  cwd: string
  workspaceId?: string
  surfaceId?: string
  windowId?: string
  workspaceName?: string
  tabTitle?: string
  pending: number
  oldestPendingAt?: number
  lastSeen: number
  ended?: boolean
}

/** Um pouso pedido pela faixa */
export type Landing = { kind: 'organizado' | 'emergencia'; startedAt: number }

/** Outra sessão com decisão pendente, como a faixa a mostra */
export type OtherSession = {
  sessionId: string
  label: string
  pending: number
  isAlive: boolean
}

declare module 'claude-code' {
  interface PluginState {
    decisoes: {
      decisions: Decision[]
      others: OtherSession[]
      now: number
      landing: Landing | null
    }
  }
}
