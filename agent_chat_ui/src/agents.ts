import type { Agent } from './types'

export const agents: Agent[] = [
  {
    id: 'scanner',
    label: 'Market Scanner',
    description: 'Scans for unusual volume and large orders',
    avatar: '◎',
  },
  {
    id: 'analyst',
    label: 'Options Analyst',
    description: 'Analyzes options flow and sentiment',
    avatar: '◈',
  },
]

export const defaultAgent = agents[1]
