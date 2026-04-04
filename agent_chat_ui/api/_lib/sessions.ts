import type Anthropic from '@anthropic-ai/sdk'

export interface DisplayMessage {
  id: string
  role: 'user' | 'assistant'
  type?: 'thinking'
  text: string
  createdAt: string
}

export interface Session {
  id: string
  agentId: string
  messages: Anthropic.MessageParam[]
  displayMessages: DisplayMessage[]
  status: 'idle' | 'streaming' | 'error'
  title: string | null
  createdAt: string
  updatedAt: string
}

const sessions = new Map<string, Session>()

export function createSession(agentId: string): Session {
  const id = crypto.randomUUID()
  const now = new Date().toISOString()
  const session: Session = {
    id,
    agentId,
    messages: [],
    displayMessages: [],
    status: 'idle',
    title: null,
    createdAt: now,
    updatedAt: now,
  }
  sessions.set(id, session)
  return session
}

export function getSession(id: string): Session | undefined {
  return sessions.get(id)
}

export function listSessions(): Session[] {
  return Array.from(sessions.values()).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  )
}

export function updateSession(id: string, patch: Partial<Pick<Session, 'status' | 'title' | 'updatedAt'>>): void {
  const s = sessions.get(id)
  if (s) Object.assign(s, patch)
}
