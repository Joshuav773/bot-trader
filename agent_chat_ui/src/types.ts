export interface Message {
  id: string
  role: 'user' | 'assistant'
  type?: 'thinking'
  content: string
  timestamp: Date
  agentId?: string
  meta?: string
}

export interface Agent {
  id: string
  label: string
  description: string
  avatar: string
}

export interface Conversation {
  id: string
  agentId: string
  title: string | null
  status: 'idle' | 'streaming' | 'error'
  createdAt: string
  updatedAt?: string
}
