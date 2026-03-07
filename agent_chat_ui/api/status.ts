import type { VercelRequest, VercelResponse } from '@vercel/node'
import { requireAuth, cursorFetch, handleError } from './_lib/cursor'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') return res.status(405).json({ ok: false })

  try {
    requireAuth(req)

    const { cursor_agent_id } = req.body ?? {}
    if (!cursor_agent_id) return res.status(400).json({ ok: false, message: 'cursor_agent_id required' })

    const statusData = await cursorFetch('GET', `/v0/agents/${cursor_agent_id}`) as Record<string, any>
    const target = (statusData.target ?? {}) as Record<string, any>

    let messages: Record<string, any>[] = []
    try {
      const convData = await cursorFetch('GET', `/v0/agents/${cursor_agent_id}/conversation`) as Record<string, any>
      messages = (convData.messages ?? []) as Record<string, any>[]
    } catch {
      // conversation may not be available yet
    }

    return res.json({
      ok: true,
      cursor_agent_id,
      status: statusData.status ?? 'UNKNOWN',
      summary: statusData.summary ?? null,
      url: target.url ?? null,
      pr_url: target.prUrl ?? null,
      messages,
    })
  } catch (err) {
    return handleError(res, err)
  }
}
