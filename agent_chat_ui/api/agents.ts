import type { VercelRequest, VercelResponse } from '@vercel/node'
import { requireAuth, cursorFetch, handleError } from './_lib/cursor.js'

function getPreviousMonday(): Date {
  const now = new Date()
  const day = now.getUTCDay()
  const daysSinceMonday = day === 0 ? 6 : day - 1
  const monday = new Date(now)
  monday.setUTCDate(now.getUTCDate() - daysSinceMonday - 7)
  monday.setUTCHours(0, 0, 0, 0)
  return monday
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'GET') return res.status(405).json({ ok: false })

  try {
    requireAuth(req)

    const data = await cursorFetch('GET', '/v0/agents?limit=100') as Record<string, any>
    const allAgents = (data.agents ?? []) as Record<string, any>[]

    const cutoff = getPreviousMonday()
    const recent = allAgents.filter((a) => {
      if (!a.createdAt) return false
      return new Date(a.createdAt) >= cutoff
    })

    return res.json({
      ok: true,
      agents: recent.map((a) => ({
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
