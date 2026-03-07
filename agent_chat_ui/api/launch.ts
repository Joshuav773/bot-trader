import type { VercelRequest, VercelResponse } from '@vercel/node'
import { requireAuth, buildPrompt, cursorFetch, handleError } from './_lib/cursor'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') return res.status(405).json({ ok: false })

  try {
    requireAuth(req)

    const { prompt, agent_id } = req.body ?? {}
    if (!prompt) return res.status(400).json({ ok: false, message: 'prompt required' })

    const repoUrl = process.env.GITHUB_REPO_URL
    if (!repoUrl) return res.status(500).json({ ok: false, message: 'GITHUB_REPO_URL not configured' })

    const fullPrompt = buildPrompt(agent_id, prompt)

    const data = await cursorFetch('POST', '/v0/agents', {
      prompt: { text: fullPrompt },
      model: process.env.CURSOR_MODEL || 'claude-4.5-sonnet-thinking',
      source: {
        repository: repoUrl,
        ref: process.env.GITHUB_REPO_REF || 'main',
      },
    }) as Record<string, any>

    const target = (data.target ?? {}) as Record<string, any>

    return res.json({
      ok: true,
      cursor_agent_id: data.id,
      status: data.status ?? 'CREATING',
      url: target.url ?? null,
    })
  } catch (err) {
    return handleError(res, err)
  }
}
