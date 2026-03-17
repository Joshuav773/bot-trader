import type { Agent } from './types'

export const agents: Agent[] = [
  {
    id: 'options-trader',
    label: 'Options Analyst',
    description: 'Quantitative options analysis powered by The Quant Oracle',
    avatar: '◈',
  },
  {
    id: 'forex-trader',
    label: 'Forex Trader',
    description: 'Currency strategy & liquidity analysis by The Global Macro Sentinel',
    avatar: '◎',
  },
]

export const defaultAgent = agents[0]
