import type { VercelRequest } from '@vercel/node'
import Anthropic from '@anthropic-ai/sdk'
import { config } from 'dotenv'
import { resolve } from 'path'
import { readFileSync } from 'fs'
import type { Session, DisplayMessage } from './sessions.js'

config({ path: resolve(process.cwd(), '.env.local') })
config({ path: resolve(process.cwd(), '../.env') })

// ── Auth (carried over from cursor.ts) ──────────────────────────────────

export class AuthError extends Error {
  status = 401
}

export function requireAuth(req: VercelRequest): void {
  const key = process.env.AGENT_CHAT_API_KEY
  if (!key) throw new AuthError('AGENT_CHAT_API_KEY not configured')

  const auth = req.headers.authorization ?? ''
  const token = auth.replace(/^Bearer\s+/i, '').trim()

  if (token !== key) throw new AuthError('Invalid API key')
}

export function handleError(res: { status: (code: number) => { json: (data: unknown) => void } }, err: unknown) {
  if (err instanceof AuthError) {
    return res.status(401).json({ ok: false, message: err.message })
  }
  const message = err instanceof Error ? err.message : 'Internal error'
  return res.status(500).json({ ok: false, message })
}

// ── Anthropic client ────────────────────────────────────────────────────

let _client: Anthropic | null = null
function client(): Anthropic {
  if (!_client) {
    const apiKey = process.env.ANTHROPIC_API_KEY
    if (!apiKey) throw new Error('ANTHROPIC_API_KEY not configured')
    _client = new Anthropic({ apiKey })
  }
  return _client
}

// ── Persona / system prompt ─────────────────────────────────────────────

const AGENT_CONFIG: Record<string, { label: string; personaFile: string }> = {
  'options-trader': { label: 'Options Analyst (The Quant Oracle)', personaFile: 'options-trader-agent.json' },
  'forex-trader': { label: 'Forex Trader (The Global Macro Sentinel)', personaFile: 'forex-trader-agent.json' },
}

const personaCache = new Map<string, string>()

function loadPersonaJson(agentId: string): string {
  if (personaCache.has(agentId)) return personaCache.get(agentId)!

  const cfg = AGENT_CONFIG[agentId] ?? AGENT_CONFIG['options-trader']
  const agentsDir = resolve(process.cwd(), '..', 'agents')
  const filePath = resolve(agentsDir, cfg.personaFile)

  try {
    const raw = readFileSync(filePath, 'utf-8')
    personaCache.set(agentId, raw)
    return raw
  } catch {
    // Fallback: try from cwd
    try {
      const alt = resolve(process.cwd(), 'agents', cfg.personaFile)
      const raw = readFileSync(alt, 'utf-8')
      personaCache.set(agentId, raw)
      return raw
    } catch {
      return JSON.stringify({ error: `Could not load ${cfg.personaFile}` })
    }
  }
}

export function buildSystemPrompt(agentId: string): string {
  const cfg = AGENT_CONFIG[agentId] ?? AGENT_CONFIG['options-trader']
  const personaJson = loadPersonaJson(agentId)

  return `You are ${cfg.label}.

Below is your full persona definition. Follow the system_prompt, analytical_framework, decision_logic, operational_scenarios/battle_plans, and all other fields exactly.

<persona>
${personaJson}
</persona>

You have access to GitHub tools that let you read files, search code, create branches, update files, and create pull requests in the repository.

## Self-Evolution
Your persona file lives at \`agents/${cfg.personaFile}\` in the repo. You should actively evolve it:

- **After meaningful conversations**: If the user shares trading preferences, risk tolerances, preferred instruments, market biases, or feedback on your analysis — use your GitHub tools to update your persona file with this new context.
- **Add to the \`learned_context\` field**: Append new entries with a date and what you learned. Create this field if it does not exist yet.
- **Refine your framework**: If a strategy or approach proves valuable (or flawed), update your \`analytical_framework\`, \`battle_plans\`/\`operational_scenarios\`, or \`decision_logic\` accordingly.
- **Be selective**: Only persist insights that will improve future conversations. Don't save trivial or one-off details.
- **Commit directly to main** with a clear message like "update persona: added user risk preference" — no branches or PRs needed for persona updates.

This is how you learn and get better over time. Each conversation should leave you sharper than the last.

Always stay in character as your persona. Provide detailed, actionable analysis grounded in your analytical framework.`
}

// ── SSE event types ─────────────────────────────────────────────────────

export interface StreamEvent {
  type: 'conversation_id' | 'text_delta' | 'thinking_delta' | 'tool_use' | 'tool_result' | 'done' | 'error'
  data: Record<string, unknown>
}

// ── MCP server config ───────────────────────────────────────────────────

function getMcpServers(): Anthropic.Beta.BetaRequestMCPServerURLDefinition[] | undefined {
  const url = process.env.GITHUB_MCP_URL
  const token = process.env.GITHUB_TOKEN
  if (!url) return undefined

  return [
    {
      type: 'url' as const,
      url,
      name: 'github',
      ...(token ? { authorization_token: token } : {}),
    },
  ]
}

function getMcpTools(): Anthropic.Beta.BetaToolUnion[] | undefined {
  if (!process.env.GITHUB_MCP_URL) return undefined
  return [
    {
      type: 'mcp_toolset' as const,
      mcp_server_name: 'github',
    },
  ]
}

// ── Streaming with MCP ──────────────────────────────────────────────────

function friendlyError(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err)
  if (raw.includes('authentication_error') || raw.includes('invalid x-api-key')) {
    return 'Invalid Anthropic API key. Check your ANTHROPIC_API_KEY in .env.'
  }
  if (raw.includes('rate_limit') || raw.includes('429')) {
    return 'Rate limited by Claude API. Please wait a moment and try again.'
  }
  if (raw.includes('overloaded') || raw.includes('529')) {
    return 'Claude API is temporarily overloaded. Try again in a few seconds.'
  }
  if (raw.includes('insufficient_quota') || raw.includes('credit')) {
    return 'No API credits remaining. Add credits at console.anthropic.com.'
  }
  return raw
}

const DEFAULT_MODEL = 'claude-sonnet-4-6-20250514'

export async function* runAgentLoop(
  session: Session,
  userMessage: string,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  // Append user message to conversation history
  session.messages.push({ role: 'user', content: userMessage })

  // Add to display messages
  const userDisplay: DisplayMessage = {
    id: crypto.randomUUID(),
    role: 'user',
    text: userMessage,
    createdAt: new Date().toISOString(),
  }
  session.displayMessages.push(userDisplay)

  // Set title from first user message
  if (!session.title) {
    session.title = userMessage.slice(0, 60) + (userMessage.length > 60 ? '...' : '')
  }

  const systemPrompt = buildSystemPrompt(session.agentId)
  const model = process.env.CLAUDE_MODEL || DEFAULT_MODEL
  const mcpServers = getMcpServers()
  const mcpTools = getMcpTools()

  // Collect the full response from streaming
  let fullText = ''
  let thinkingText = ''

  try {
    // Build request params — use beta endpoint when MCP servers are configured
    const baseParams = {
      model,
      max_tokens: 16000,
      system: systemPrompt,
      messages: session.messages,
    }

    if (mcpServers) {
      // Beta endpoint with MCP — tool execution is automatic
      const betaStream = client().beta.messages.stream({
        ...baseParams,
        mcp_servers: mcpServers,
        tools: mcpTools,
        betas: ['mcp-client-2025-11-20'],
      })

      for await (const event of betaStream) {
        if (signal?.aborted) {
          betaStream.abort()
          yield { type: 'done', data: { status: 'stopped' } }
          return
        }
        if (event.type === 'content_block_delta') {
          if ('text' in event.delta && event.delta.type === 'text_delta') {
            fullText += event.delta.text
            yield { type: 'text_delta', data: { text: event.delta.text } }
          } else if ('thinking' in event.delta && event.delta.type === 'thinking_delta') {
            thinkingText += event.delta.thinking
            yield { type: 'thinking_delta', data: { text: event.delta.thinking } }
          }
        } else if (event.type === 'content_block_start') {
          if (event.content_block.type === 'mcp_tool_use') {
            yield { type: 'tool_use', data: { tool: event.content_block.name, server: event.content_block.server_name } }
          }
        }
      }

      const finalMessage = await betaStream.finalMessage()
      // Beta content blocks include MCP types that don't fit standard MessageParam — cast through unknown
      session.messages.push({ role: 'assistant', content: finalMessage.content as unknown as Anthropic.ContentBlockParam[] })
    } else {
      // Standard endpoint without MCP
      const stdStream = client().messages.stream(baseParams)

      for await (const event of stdStream) {
        if (signal?.aborted) {
          stdStream.abort()
          yield { type: 'done', data: { status: 'stopped' } }
          return
        }
        if (event.type === 'content_block_delta') {
          if ('text' in event.delta && event.delta.type === 'text_delta') {
            fullText += event.delta.text
            yield { type: 'text_delta', data: { text: event.delta.text } }
          } else if ('thinking' in event.delta && event.delta.type === 'thinking_delta') {
            thinkingText += event.delta.thinking
            yield { type: 'thinking_delta', data: { text: event.delta.thinking } }
          }
        }
      }

      const finalMessage = await stdStream.finalMessage()
      session.messages.push({ role: 'assistant', content: finalMessage.content as Anthropic.ContentBlock[] })
    }

  } catch (err) {
    const message = friendlyError(err)
    yield { type: 'error', data: { message } }
    return
  }

  // Add thinking to display messages if present
  if (thinkingText) {
    session.displayMessages.push({
      id: crypto.randomUUID(),
      role: 'assistant',
      type: 'thinking',
      text: thinkingText,
      createdAt: new Date().toISOString(),
    })
  }

  // Add text response to display messages if present
  if (fullText) {
    session.displayMessages.push({
      id: crypto.randomUUID(),
      role: 'assistant',
      text: fullText,
      createdAt: new Date().toISOString(),
    })
  }

  yield { type: 'done', data: { status: 'finished' } }
}
