import type { VercelRequest, VercelResponse } from '@vercel/node'
import { requireAuth, cursorFetch, handleError } from './_lib/cursor.js'

// Hard cutoff: only show agents created on or after this date.
// This is set to last Monday in UTC. Adjust if you want to widen/narrow history.
const AGENT_HISTORY_CUTOFF = new Date('2026-02-09T00:00:00Z')

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'GET') return res.status(405).json({ ok: false })

  try {
    requireAuth(req)

    const data = await cursorFetch('GET', '/v0/agents?limit=100') as Record<string, any>
    const allAgents = (data.agents ?? []) as Record<string, any>[]

    const recent = allAgents.filter((a) => {
      if (!a.createdAt) return false
      return new Date(a.createdAt) >= AGENT_HISTORY_CUTOFF
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
