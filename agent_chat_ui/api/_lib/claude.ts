import type { VercelRequest } from '@vercel/node'
import Anthropic from '@anthropic-ai/sdk'
import { config } from 'dotenv'
import { resolve } from 'path'
import { readFileSync, readdirSync, existsSync } from 'fs'
import type { Session, DisplayMessage } from './sessions.js'
import { saveSession } from './sessions.js'

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

const AGENT_CONFIG: Record<string, { label: string }> = {
  'options-trader': { label: 'Options Analyst (The Quant Oracle)' },
  'forex-trader': { label: 'Forex Trader (The Global Macro Sentinel)' },
}

// Resolve the agents/ directory — first try sibling of cwd, fall back to cwd itself
function agentsRoot(): string {
  const sibling = resolve(process.cwd(), '..', 'agents')
  if (existsSync(sibling)) return sibling
  return resolve(process.cwd(), 'agents')
}

function agentFolder(agentId: string): string {
  return resolve(agentsRoot(), agentId)
}

const personaCache = new Map<string, string>()

function loadPersonaJson(agentId: string): string {
  if (personaCache.has(agentId)) return personaCache.get(agentId)!

  const filePath = resolve(agentFolder(agentId), `${agentId}-agent.json`)
  try {
    const raw = readFileSync(filePath, 'utf-8')
    personaCache.set(agentId, raw)
    return raw
  } catch {
    return JSON.stringify({ error: `Could not load ${filePath}` })
  }
}

function loadContextFiles(agentId: string): { name: string; content: string }[] {
  const contextDir = resolve(agentFolder(agentId), 'context')
  if (!existsSync(contextDir)) return []

  try {
    const files = readdirSync(contextDir)
      .filter((f) => f.endsWith('.md'))
      .sort()
    return files.map((name) => ({
      name,
      content: readFileSync(resolve(contextDir, name), 'utf-8'),
    }))
  } catch {
    return []
  }
}

export function buildSystemPrompt(agentId: string): string {
  const cfg = AGENT_CONFIG[agentId] ?? AGENT_CONFIG['options-trader']
  const personaJson = loadPersonaJson(agentId)
  const contextFiles = loadContextFiles(agentId)

  const contextSection = contextFiles.length
    ? `\n<context_files>\n${contextFiles
        .map((f) => `<file path="agents/${agentId}/context/${f.name}">\n${f.content}\n</file>`)
        .join('\n\n')}\n</context_files>\n\nThe files above contain your protocols, learned behaviors, ledgers, and operational context. Use them on every response — they define how you think and respond. Update them as you learn new things.\n`
    : ''

  return `You are ${cfg.label}.

Below is your full persona definition. Follow the system_prompt, analytical_framework, decision_logic, operational_scenarios/battle_plans, and all other fields exactly.

<persona>
${personaJson}
</persona>
${contextSection}
You have access to GitHub tools that let you read files, search code, create branches, update files, and create pull requests in the repository.

## Self-Evolution
Your files live in \`agents/${agentId}/\` in the repo:
- Persona: \`agents/${agentId}/${agentId}-agent.json\`
- Context (protocols, ledgers, learnings): \`agents/${agentId}/context/*.md\`

You should actively evolve these:

- **After meaningful conversations**: If the user shares trading preferences, risk tolerances, preferred instruments, market biases, or feedback on your analysis — use your GitHub tools to update your persona or context files.
- **Add to the \`learned_context\` field** in your persona JSON for structured learnings.
- **Create or update context markdown files** for protocols, ledgers, trade journals, or reference material. Use clear filenames like \`ACCOUNT_LEDGER.md\`, \`PROTOCOL.md\`, \`MARKET_REGIME.md\`.
- **Refine your framework**: If a strategy proves valuable (or flawed), update your \`analytical_framework\`, \`battle_plans\`/\`operational_scenarios\`, or \`decision_logic\` accordingly.
- **Be selective**: Only persist insights that will improve future conversations.
- **Commit directly to main** with a clear message like "update persona: added user risk preference".

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

const DEFAULT_MODEL = 'claude-sonnet-4-6'

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

  // Persist user message immediately so a mid-stream failure doesn't lose it
  saveSession(session)

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

  // Persist full assistant response so follow-ups see complete history
  session.updatedAt = new Date().toISOString()
  saveSession(session)

  yield { type: 'done', data: { status: 'finished' } }
}
