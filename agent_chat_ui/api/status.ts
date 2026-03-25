import type { VercelRequest, VercelResponse } from '@vercel/node'
import {
  requireAuth,
  cursorFetch,
  handleError,
  agentMatchesConfiguredRepository,
  getConversationTailLimit,
  tailConversationMessages,
  detectPersonaFromMessages,
} from './_lib/cursor.js'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') return res.status(405).json({ ok: false })

  try {
    requireAuth(req)

    const { cursor_agent_id } = req.body ?? {}
    if (!cursor_agent_id) return res.status(400).json({ ok: false, message: 'cursor_agent_id required' })

    const statusData = await cursorFetch('GET', `/v0/agents/${cursor_agent_id}`) as Record<string, any>
    const target = (statusData.target ?? {}) as Record<string, any>

    if (!agentMatchesConfiguredRepository(statusData as Record<string, unknown>)) {
      return res.status(404).json({
        ok: false,
        message: 'Agent is not associated with this app repository.',
      })
    }

    let messages: Record<string, any>[] = []
    let messages_total: number | undefined
    let messages_truncated = false
    let persona_id: string | null = null
    try {
      const convData = await cursorFetch('GET', `/v0/agents/${cursor_agent_id}/conversation`) as Record<string, any>
      const all = (convData.messages ?? []) as Record<string, any>[]
      persona_id = detectPersonaFromMessages(all)
      const limit = getConversationTailLimit()
      const { tail, total, truncated } = tailConversationMessages(all, limit)
      messages = tail
      messages_total = truncated ? total : undefined
      messages_truncated = truncated
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
      messages_truncated,
      ...(messages_total !== undefined ? { messages_total } : {}),
      ...(persona_id ? { persona_id } : {}),
    })
  } catch (err) {
    return handleError(res, err)
  }
}
