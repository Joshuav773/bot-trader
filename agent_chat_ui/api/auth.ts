import type { VercelRequest, VercelResponse } from '@vercel/node'
import './_lib/cursor'

export default function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') return res.status(405).json({ ok: false })

  const key = process.env.AGENT_CHAT_API_KEY
  const { api_key } = req.body ?? {}

  if (!key || api_key !== key) {
    return res.status(401).json({ ok: false, message: 'Invalid API key' })
  }

  return res.json({ ok: true })
}
