import type { VercelRequest, VercelResponse } from '@vercel/node'
import { requireAuth, buildPrompt, cursorFetch, handleError } from './_lib/cursor'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') return res.status(405).json({ ok: false })

  try {
    requireAuth(req)

    const { prompt, agent_id, cursor_agent_id } = req.body ?? {}
    if (!prompt) return res.status(400).json({ ok: false, message: 'prompt required' })
    if (!cursor_agent_id) return res.status(400).json({ ok: false, message: 'cursor_agent_id required' })

    const fullPrompt = buildPrompt(agent_id, prompt)

    await cursorFetch('POST', `/v0/agents/${cursor_agent_id}/followup`, {
      prompt: { text: fullPrompt },
    })

    return res.json({
      ok: true,
      cursor_agent_id,
      status: 'RUNNING',
    })
  } catch (err) {
    return handleError(res, err)
  }
}
