import type { VercelRequest, VercelResponse } from '@vercel/node'
import { requireAuth, handleError } from './_lib/claude.js'
import { getSession, listSessions } from './_lib/sessions.js'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'GET') return res.status(405).json({ ok: false })

  try {
    requireAuth(req)

    const id = req.query.id as string | undefined

    // Single conversation
    if (id) {
      const session = getSession(id)
      if (!session) return res.status(404).json({ ok: false, message: 'Conversation not found' })

      return res.json({
        ok: true,
        conversation: {
          id: session.id,
          agentId: session.agentId,
          title: session.title,
          status: session.status,
          createdAt: session.createdAt,
          updatedAt: session.updatedAt,
          messages: session.displayMessages,
        },
      })
    }

    // List all conversations
    const sessions = listSessions()
    return res.json({
      ok: true,
      conversations: sessions.map((s) => ({
        id: s.id,
        agentId: s.agentId,
        title: s.title,
        status: s.status,
        createdAt: s.createdAt,
        updatedAt: s.updatedAt,
      })),
    })
  } catch (err) {
    return handleError(res, err)
  }
}
