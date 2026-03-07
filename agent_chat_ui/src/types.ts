export interface Message {
  id: string
  role: 'user' | 'agent'
  type?: 'assistant_message' | 'user_message' | 'thinking' | string
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
