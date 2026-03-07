import type { VercelRequest, VercelResponse } from '@vercel/node'
import { requireAuth, cursorFetch, handleError } from './_lib/cursor.js'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') return res.status(405).json({ ok: false })

  try {
    requireAuth(req)

    const { cursor_agent_id } = req.body ?? {}
    if (!cursor_agent_id) return res.status(400).json({ ok: false, message: 'cursor_agent_id required' })

    await cursorFetch('POST', `/v0/agents/${cursor_agent_id}/stop`)

    return res.json({ ok: true, cursor_agent_id })
  } catch (err) {
    return handleError(res, err)
  }
}
