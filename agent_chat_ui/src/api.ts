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

export interface LaunchResponse {
  ok: boolean
  cursor_agent_id: string | null
  status: string | null
  url: string | null
  message?: string
}

export async function launchAgent(prompt: string, agentId: string): Promise<LaunchResponse> {
  const res = await authedFetch(`${BASE}/launch`, {
    method: 'POST',
    body: JSON.stringify({ prompt, agent_id: agentId }),
  })
  if (!res.ok && res.status !== 401) throw new Error(`Server error: ${res.status}`)
  return res.json()
}

export async function followUp(prompt: string, agentId: string, cursorAgentId: string): Promise<LaunchResponse> {
  const res = await authedFetch(`${BASE}/followup`, {
    method: 'POST',
    body: JSON.stringify({ prompt, agent_id: agentId, cursor_agent_id: cursorAgentId }),
  })
  if (!res.ok && res.status !== 401) throw new Error(`Server error: ${res.status}`)
  return res.json()
}

export interface StatusResponse {
  ok: boolean
  cursor_agent_id: string
  status: string
  summary: string | null
  url: string | null
  pr_url: string | null
  messages: { id: string; type: string; text: string }[]
  message?: string
}

export async function pollStatus(cursorAgentId: string): Promise<StatusResponse> {
  const res = await authedFetch(`${BASE}/status`, {
    method: 'POST',
    body: JSON.stringify({ cursor_agent_id: cursorAgentId }),
  })
  if (!res.ok && res.status !== 401) throw new Error(`Server error: ${res.status}`)
  return res.json()
}

export async function stopAgent(cursorAgentId: string) {
  await authedFetch(`${BASE}/stop`, {
    method: 'POST',
    body: JSON.stringify({ cursor_agent_id: cursorAgentId }),
  })
}

export interface AgentListItem {
  id: string
  name: string | null
  status: string
  summary: string | null
  createdAt: string
}

export async function listAgents(): Promise<AgentListItem[]> {
  const res = await authedFetch(`${BASE}/agents`)
  if (!res.ok && res.status !== 401) throw new Error(`Server error: ${res.status}`)
  const data = await res.json()
  return data.agents ?? []
}
