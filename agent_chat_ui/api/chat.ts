import type { VercelRequest, VercelResponse } from '@vercel/node'
import { requireAuth, handleError, runAgentLoop } from './_lib/claude.js'
import { createSession, getSession, updateSession } from './_lib/sessions.js'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') return res.status(405).json({ ok: false })

  try {
    requireAuth(req)

    const { prompt, agent_id, conversation_id } = req.body ?? {}
    if (!prompt) return res.status(400).json({ ok: false, message: 'prompt required' })

    const agentId = agent_id || 'options-trader'

    // Get or create session
    let session
    if (conversation_id) {
      session = getSession(conversation_id)
      if (!session) return res.status(404).json({ ok: false, message: 'Conversation not found. Start a new one.' })
    } else {
      session = createSession(agentId)
    }

    session.status = 'streaming'
    updateSession(session.id, { status: 'streaming', updatedAt: new Date().toISOString() })

    // Set SSE headers
    res.setHeader('Content-Type', 'text/event-stream')
    res.setHeader('Cache-Control', 'no-cache, no-transform')
    res.setHeader('Connection', 'keep-alive')
    res.setHeader('X-Accel-Buffering', 'no')

    // Send conversation ID immediately
    res.write(`data: ${JSON.stringify({ type: 'conversation_id', id: session.id, agent_id: session.agentId })}\n\n`)

    // Detect client disconnect
    const abortController = new AbortController()
    req.on('close', () => abortController.abort())

    // Run the agentic loop and stream events
    try {
      for await (const event of runAgentLoop(session, prompt, abortController.signal)) {
        if (abortController.signal.aborted) break
        res.write(`data: ${JSON.stringify(event)}\n\n`)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Stream error'
      res.write(`data: ${JSON.stringify({ type: 'error', data: { message } })}\n\n`)
      updateSession(session.id, { status: 'error', updatedAt: new Date().toISOString() })
    }

    updateSession(session.id, { status: 'idle', updatedAt: new Date().toISOString() })
    res.end()
  } catch (err) {
    // If headers already sent (streaming started), just end
    if (res.headersSent) {
      res.end()
    } else {
      return handleError(res, err)
    }
  }
}
