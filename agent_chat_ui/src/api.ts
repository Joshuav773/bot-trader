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

export interface AgentResponse {
  ok: boolean
  agent_cursor_id: string | null
  status: string | null
  message: string
  url: string | null
}

export async function launchAgent(prompt: string, agentId: string): Promise<AgentResponse> {
  const res = await authedFetch(`${BASE}/launch`, {
    method: 'POST',
    body: JSON.stringify({ prompt, agent_id: agentId }),
  })
  if (!res.ok) throw new Error(`Server error: ${res.status}`)
  return res.json()
}

export async function followUp(prompt: string, agentId: string): Promise<AgentResponse> {
  const res = await authedFetch(`${BASE}/followup`, {
    method: 'POST',
    body: JSON.stringify({ prompt, agent_id: agentId }),
  })
  if (!res.ok) throw new Error(`Server error: ${res.status}`)
  return res.json()
}

export interface SSECallbacks {
  onStatus: (data: { status: string; summary?: string; url?: string; pr_url?: string }) => void
  onMessage: (data: { id: string; type: string; text: string }) => void
  onDone: (data: { status: string; summary?: string }) => void
  onError: (data: { message: string }) => void
}

export function streamConversation(persona: string, callbacks: SSECallbacks): () => void {
  const key = getStoredKey() || ''
  const es = new EventSource(`${BASE}/stream/${persona}?key=${encodeURIComponent(key)}`)

  es.addEventListener('status', (e) => {
    callbacks.onStatus(JSON.parse(e.data))
  })

  es.addEventListener('message', (e) => {
    callbacks.onMessage(JSON.parse(e.data))
  })

  es.addEventListener('done', (e) => {
    callbacks.onDone(JSON.parse(e.data))
    es.close()
  })

  es.addEventListener('error', (e) => {
    if (e instanceof MessageEvent) {
      callbacks.onError(JSON.parse(e.data))
    } else {
      callbacks.onError({ message: 'Connection lost' })
    }
    es.close()
  })

  return () => es.close()
}

export async function clearAgent(agentId: string) {
  await authedFetch(`${BASE}/clear`, {
    method: 'POST',
    body: JSON.stringify({ agent_id: agentId }),
  })
}

export async function stopAgent(agentId: string) {
  await authedFetch(`${BASE}/stop`, {
    method: 'POST',
    body: JSON.stringify({ agent_id: agentId }),
  })
}
