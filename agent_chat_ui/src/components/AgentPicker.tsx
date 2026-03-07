import { agents } from '../agents'
import type { Agent } from '../types'

interface Props {
  selected: Agent
  onSelect: (agent: Agent) => void
}

export default function AgentPicker({ selected, onSelect }: Props) {
  return (
    <select
      value={selected.id}
      onChange={(e) => {
        const agent = agents.find((a) => a.id === e.target.value)
        if (agent) onSelect(agent)
      }}
      className="
        bg-surface border border-border rounded-lg text-sm text-text
        px-3 py-1.5 font-medium cursor-pointer
        focus:outline-none focus:border-border-focus
        transition-colors duration-150
        appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20fill%3D%22%23888%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M8%2011L3%206h10z%22%2F%3E%3C%2Fsvg%3E')]
        bg-no-repeat bg-[right_0.5rem_center] pr-7
      "
    >
      {agents.map((agent) => (
        <option key={agent.id} value={agent.id}>
          {agent.avatar} {agent.label}
        </option>
      ))}
    </select>
  )
}
