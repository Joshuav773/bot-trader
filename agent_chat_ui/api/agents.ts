import type { VercelRequest, VercelResponse } from '@vercel/node'
import { requireAuth, cursorFetch, handleError } from './_lib/cursor.js'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'GET') return res.status(405).json({ ok: false })

  try {
    requireAuth(req)

    const data = await cursorFetch('GET', '/v0/agents?limit=100') as Record<string, any>
    const allAgents = (data.agents ?? []) as Record<string, any>[]

    const visible = allAgents.filter((a) => {
      const status = (a.status ?? '').toString().toUpperCase()
      return status !== 'EXPIRED'
    })

    return res.json({
      ok: true,
      agents: visible.map((a) => ({
        id: a.id,
        name: a.name ?? null,
        status: a.status ?? 'UNKNOWN',
        summary: a.summary ?? null,
        createdAt: a.createdAt,
      })),
    })
  } catch (err) {
    return handleError(res, err)
  }
}
