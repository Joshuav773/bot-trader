const BASE = '/api'
const STORAGE_KEY = 'agent_chat_api_key'

export function getStoredKey(): string | null {
  return localStorage.getItem(STORAGE_KEY)
}

export function storeKey(key: string) {
  localStorage.setItem(STORAGE_KEY, key)
}

export function clearKey() {
  localStorage.removeItem(STORAGE_KEY)
}

function authHeaders(): Record<string, string> {
  const key = getStoredKey()
  return {
    'Content-Type': 'application/json',
    ...(key ? { Authorization: `Bearer ${key}` } : {}),
  }
}

async function authedFetch(url: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(url, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers ?? {}) },
  })
  if (res.status === 401) {
    clearKey()
    window.location.reload()
  }
  return res
}

export async function authenticate(apiKey: string): Promise<boolean> {
  const res = await fetch(`${BASE}/auth`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  })
  if (res.ok) {
    storeKey(apiKey)
    return true
  }
  return false
}

// ── Streaming chat ──────────────────────────────────────────────────────

export interface StreamCallbacks {
  onConversationId: (id: string, agentId: string) => void
  onToken: (text: string) => void
  onThinking: (text: string) => void
  onToolUse: (tool: string, input: Record<string, unknown>) => void
  onToolResult: (tool: string, result: string) => void
  onDone: () => void
  onError: (err: Error) => void
}

export function streamChat(
  conversationId: string | null,
  prompt: string,
  agentId: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): void {
  const url = `${BASE}/chat`
  const body = JSON.stringify({
    prompt,
    agent_id: agentId,
    conversation_id: conversationId,
  })

  fetch(url, {
    method: 'POST',
    headers: authHeaders(),
    body,
    signal,
  })
    .then(async (res) => {
      if (res.status === 401) {
        clearKey()
        window.location.reload()
        return
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        callbacks.onError(new Error(data.message || `Server error: ${res.status}`))
        return
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop()! // keep incomplete line in buffer

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data: ')) continue

          try {
            const payload = JSON.parse(trimmed.slice(6))
            const type = payload.type ?? payload.data?.type

            switch (type) {
              case 'conversation_id':
                callbacks.onConversationId(payload.id ?? payload.data?.id, payload.agent_id ?? payload.data?.agent_id)
                break
              case 'text_delta':
                callbacks.onToken(payload.data?.text ?? payload.text ?? '')
                break
              case 'thinking_delta':
                callbacks.onThinking(payload.data?.text ?? payload.text ?? '')
                break
              case 'tool_use':
                callbacks.onToolUse(payload.data?.tool ?? '', payload.data?.input ?? {})
                break
              case 'tool_result':
                callbacks.onToolResult(payload.data?.tool ?? '', payload.data?.result ?? '')
                break
              case 'done':
                callbacks.onDone()
                break
              case 'error':
                callbacks.onError(new Error(payload.data?.message ?? 'Unknown error'))
                break
            }
          } catch {
            // Ignore malformed SSE lines
          }
        }
      }

      // If stream ended without an explicit done event, notify done
      callbacks.onDone()
    })
    .catch((err) => {
      if (err.name === 'AbortError') {
        callbacks.onDone()
        return
      }
      callbacks.onError(err)
    })
}

// ── Conversations ───────────────────────────────────────────────────────

export interface ConversationListItem {
  id: string
  agentId: string
  title: string | null
  status: string
  createdAt: string
}

export interface ConversationDetail {
  id: string
  agentId: string
  title: string | null
  status: string
  messages: { id: string; role: 'user' | 'assistant'; type?: 'thinking'; text: string; createdAt: string }[]
}

export async function listConversations(): Promise<ConversationListItem[]> {
  const res = await authedFetch(`${BASE}/conversations`)
  if (!res.ok && res.status !== 401) throw new Error(`Server error: ${res.status}`)
  const data = await res.json()
  return data.conversations ?? []
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  const res = await authedFetch(`${BASE}/conversations?id=${encodeURIComponent(id)}`)
  if (!res.ok && res.status !== 401) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.message ?? `Server error: ${res.status}`)
  }
  const data = await res.json()
  return data.conversation
}
