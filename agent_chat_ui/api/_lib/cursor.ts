import type { VercelRequest } from '@vercel/node'
import { config } from 'dotenv'
import { resolve } from 'path'

config({ path: resolve(process.cwd(), '.env.local') })
config({ path: resolve(process.cwd(), '../.env') })

const CURSOR_BASE = 'https://api.cursor.com'

const AGENT_CONFIG: Record<string, { label: string; personaFile: string }> = {
  'options-trader': { label: 'Options Analyst (The Quant Oracle)', personaFile: 'options-trader-agent.json' },
  'forex-trader': { label: 'Forex Trader (The Global Macro Sentinel)', personaFile: 'forex-trader-agent.json' },
}

export function requireAuth(req: VercelRequest): void {
  const key = process.env.AGENT_CHAT_API_KEY
  if (!key) throw new AuthError('AGENT_CHAT_API_KEY not configured')

  const auth = req.headers.authorization ?? ''
  const token = auth.replace(/^Bearer\s+/i, '').trim()

  if (token !== key) throw new AuthError('Invalid API key')
}

export class AuthError extends Error {
  status = 401
}

export function buildPrompt(agentId: string | undefined, userPrompt: string): string {
  const config = AGENT_CONFIG[agentId ?? ''] ?? AGENT_CONFIG['options-trader']
  return `You are ${config.label}. Read and adopt the full persona defined in agents/${config.personaFile} — follow its system_prompt and all other fields (analytical_framework, decision_logic, operational_scenarios, etc.) exactly.\n\n${userPrompt}`
}

/** Normalizes GitHub repo URLs / SSH forms to `owner/repo` for comparison. */
function canonicalGitHubRepoKey(raw: string | undefined): string {
  if (!raw?.trim()) return ''
  let s = raw.trim().replace(/\.git$/i, '')
  const ssh = s.match(/^git@github\.com:(.+)$/i)
  if (ssh) {
    return ssh[1].replace(/^\/+|\/+$/g, '').toLowerCase()
  }
  try {
    const url = new URL(s.includes('://') ? s : `https://${s}`)
    const host = url.hostname.toLowerCase()
    if (host === 'github.com' || host.endsWith('.github.com')) {
      const path = url.pathname.replace(/^\//, '').replace(/\/$/, '')
      return path.toLowerCase()
    }
    return `${host}${url.pathname}`.replace(/\/+$/, '').toLowerCase()
  } catch {
    return s.toLowerCase()
  }
}

/** PR URLs like https://github.com/org/repo/pull/123 → org/repo */
function repoKeyFromGitHubPrUrl(prUrl: string): string {
  const m = prUrl.match(/github\.com\/([^/]+\/[^/]+)\/pull\//i)
  return m ? m[1].toLowerCase() : ''
}

/**
 * True if this agent's source matches GITHUB_REPO_URL (bot-trader).
 * When GITHUB_REPO_URL is unset, does not filter (backward compatible).
 */
export function agentMatchesConfiguredRepository(agent: Record<string, unknown>): boolean {
  const expected = process.env.GITHUB_REPO_URL?.trim()
  if (!expected) return true

  const want = canonicalGitHubRepoKey(expected)
  if (!want) return true

  const source = agent.source as Record<string, unknown> | undefined
  const target = agent.target as Record<string, unknown> | undefined
  const repoUrl = typeof source?.repository === 'string' ? source.repository : ''
  const prUrl = typeof source?.prUrl === 'string' ? source.prUrl : ''
  const targetPrUrl = typeof target?.prUrl === 'string' ? target.prUrl : ''

  if (repoUrl && canonicalGitHubRepoKey(repoUrl) === want) return true
  for (const p of [prUrl, targetPrUrl]) {
    if (p) {
      const fromPr = repoKeyFromGitHubPrUrl(p)
      if (fromPr && fromPr === want) return true
    }
  }
  return false
}

const PERSONA_IDS = Object.keys(AGENT_CONFIG)

/**
 * Tier 3 (source of truth): extract persona from the first user message,
 * which always starts with "You are ... agents/<id>-agent.json".
 */
export function detectPersonaFromMessages(messages: Record<string, any>[]): string | null {
  const first = messages.find((m) => m.type === 'user_message')
  if (!first?.text) return null
  const match = first.text.match(/agents\/([a-z][\w-]*)-agent\.json/)
  if (match && PERSONA_IDS.includes(match[1])) return match[1]
  return null
}

/**
 * Tier 2 (heuristic for sidebar): infer persona from Cursor-generated agent name.
 */
export function inferPersonaFromName(name: string | null | undefined): string | null {
  if (!name) return null
  const lower = name.toLowerCase()
  if (lower.includes('forex') || lower.includes('currency') || lower.includes('macro') || lower.includes('fx ')) return 'forex-trader'
  if (lower.includes('option') || lower.includes('quant') || lower.includes('greek') || lower.includes('theta') || lower.includes('volatil')) return 'options-trader'
  return null
}

const DEFAULT_CONVERSATION_TAIL = 80

export function getConversationTailLimit(): number {
  const raw = process.env.AGENT_CHAT_CONVERSATION_TAIL
  if (raw === undefined || raw === '') return DEFAULT_CONVERSATION_TAIL
  const n = Number.parseInt(raw, 10)
  if (!Number.isFinite(n) || n < 1) return DEFAULT_CONVERSATION_TAIL
  return Math.min(n, 500)
}

export function tailConversationMessages<T>(messages: T[], limit: number): { tail: T[]; total: number; truncated: boolean } {
  const total = messages.length
  if (total <= limit) return { tail: messages, total, truncated: false }
  return { tail: messages.slice(-limit), total, truncated: true }
}

export async function cursorFetch(
  method: 'GET' | 'POST' | 'DELETE',
  path: string,
  body?: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const apiKey = process.env.CURSOR_API_KEY
  if (!apiKey) throw new Error('CURSOR_API_KEY not configured')

  const encoded = Buffer.from(`${apiKey}:`).toString('base64')

  const res = await fetch(`${CURSOR_BASE}${path}`, {
    method,
    headers: {
      Authorization: `Basic ${encoded}`,
      'Content-Type': 'application/json',
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Cursor API ${res.status}: ${text}`)
  }

  return res.json()
}

export function handleError(res: { status: (code: number) => { json: (data: unknown) => void } }, err: unknown) {
  if (err instanceof AuthError) {
    return res.status(401).json({ ok: false, message: err.message })
  }
  const message = err instanceof Error ? err.message : 'Internal error'
  return res.status(500).json({ ok: false, message })
}
