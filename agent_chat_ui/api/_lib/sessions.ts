import type Anthropic from '@anthropic-ai/sdk'
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs'
import { dirname, resolve } from 'path'
import { tmpdir } from 'os'

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

// Persist to /tmp so the session survives across serverless function invocations.
// Note: in Vercel production /tmp is lambda-scoped (shared within a warm instance
// but lost on cold start). For true persistence use Vercel KV or a database.
const STORAGE_PATH = resolve(tmpdir(), 'bot-trader-sessions.json')

function readAll(): Map<string, Session> {
  if (!existsSync(STORAGE_PATH)) return new Map()
  try {
    const raw = readFileSync(STORAGE_PATH, 'utf-8')
    const entries = JSON.parse(raw) as [string, Session][]
    return new Map(entries)
  } catch {
    return new Map()
  }
}

function writeAll(sessions: Map<string, Session>): void {
  try {
    const dir = dirname(STORAGE_PATH)
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
    writeFileSync(STORAGE_PATH, JSON.stringify(Array.from(sessions.entries())))
  } catch {
    // ignore write failures — worst case session is lost and user starts a new one
  }
}

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
  const sessions = readAll()
  sessions.set(id, session)
  writeAll(sessions)
  return session
}

export function getSession(id: string): Session | undefined {
  return readAll().get(id)
}

export function listSessions(): Session[] {
  return Array.from(readAll().values()).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  )
}

export function saveSession(session: Session): void {
  const sessions = readAll()
  sessions.set(session.id, session)
  writeAll(sessions)
}

export function updateSession(id: string, patch: Partial<Pick<Session, 'status' | 'title' | 'updatedAt'>>): void {
  const sessions = readAll()
  const s = sessions.get(id)
  if (s) {
    Object.assign(s, patch)
    writeAll(sessions)
  }
}
