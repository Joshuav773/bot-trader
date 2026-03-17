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
