import type { VercelRequest } from '@vercel/node'

const CURSOR_BASE = 'https://api.cursor.com'

const AGENT_LABELS: Record<string, string> = {
  analyst: 'Options Analyst',
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
  const label = AGENT_LABELS[agentId ?? ''] ?? agentId ?? 'Agent'
  return `Adopt the persona: options-trader-agent. Follow the instructions in the agents/ folder for this persona.\n\n${userPrompt}`
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

export function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export function errorResponse(err: unknown) {
  if (err instanceof AuthError) {
    return json({ ok: false, message: err.message }, 401)
  }
  const message = err instanceof Error ? err.message : 'Internal error'
  return json({ ok: false, message }, 500)
}
