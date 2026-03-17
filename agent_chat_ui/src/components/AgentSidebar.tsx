import { useState, useEffect } from 'react'
import type { AgentListItem } from '../api'
import type { Agent } from '../types'
import { listAgents } from '../api'
import { agents as agentPresets } from '../agents'

interface Props {
  open: boolean
  onClose: () => void
  activeId: string | null
  selectedAgent: Agent
  onSelectAgent: (agent: Agent) => void
  onSelectHistory: (id: string) => void
  onNew: () => void
  onLogout: () => void
  isRunning: boolean
  onStop: () => void
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

function groupByTime(items: AgentListItem[]): { label: string; agents: AgentListItem[] }[] {
  const now = Date.now()
  const dayMs = 86400000
  const todayStart = new Date()
  todayStart.setHours(0, 0, 0, 0)

  const groups: { label: string; agents: AgentListItem[] }[] = [
    { label: 'Today', agents: [] },
    { label: 'This Week', agents: [] },
    { label: 'This Month', agents: [] },
    { label: 'Older', agents: [] },
  ]

  for (const a of items) {
    const t = new Date(a.createdAt).getTime()
    if (t >= todayStart.getTime()) {
      groups[0].agents.push(a)
    } else if (now - t < 7 * dayMs) {
      groups[1].agents.push(a)
    } else if (now - t < 30 * dayMs) {
      groups[2].agents.push(a)
    } else {
      groups[3].agents.push(a)
    }
  }

  return groups.filter((g) => g.agents.length > 0)
}

const STATUS_DOT: Record<string, string> = {
  RUNNING: 'bg-blue-400 animate-pulse',
  CREATING: 'bg-blue-400 animate-pulse',
  FINISHED: 'bg-green-500',
  STOPPED: 'bg-neutral-500',
  ERRORED: 'bg-red-400',
}

export default function AgentSidebar({
  open,
  onClose,
  activeId,
  selectedAgent,
  onSelectAgent,
  onSelectHistory,
  onNew,
  onLogout,
  isRunning,
  onStop,
}: Props) {
  const [agents, setAgents] = useState<AgentListItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    listAgents()
      .then(setAgents)
      .catch(() => setAgents([]))
      .finally(() => setLoading(false))
  }, [])

  const groups = groupByTime(agents)

  const sidebar = (
    <div className="w-[260px] flex-shrink-0 h-full flex flex-col border-r border-border bg-[#1a1a1a]">
      {/* New Agent button */}
      <div className="px-3 pt-3 pb-2">
        <button
          onClick={() => { onNew(); onClose() }}
          className="
            w-full flex items-center gap-2 px-3 py-2 rounded-lg
            text-[13px] font-medium text-text
            hover:bg-white/[0.06] transition-colors cursor-pointer
          "
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M8 3v10M3 8h10" />
          </svg>
          New Agent
        </button>
      </div>

      {/* Agent persona picker */}
      <div className="px-3 pb-2">
        <select
          value={selectedAgent.id}
          onChange={(e) => {
            const a = agentPresets.find((p) => p.id === e.target.value)
            if (a) onSelectAgent(a)
          }}
          className="
            w-full bg-white/[0.04] border border-white/[0.08] rounded-lg
            text-[12px] text-text-secondary px-2.5 py-1.5 cursor-pointer
            focus:outline-none focus:border-white/[0.15]
            transition-colors appearance-none
            bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2210%22%20height%3D%2210%22%20fill%3D%22%23666%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M8%2011L3%206h10z%22%2F%3E%3C%2Fsvg%3E')]
            bg-no-repeat bg-[right_0.5rem_center] pr-6
          "
        >
          {agentPresets.map((a) => (
            <option key={a.id} value={a.id}>{a.avatar} {a.label}</option>
          ))}
        </select>
      </div>

      <div className="mx-3 border-t border-white/[0.06]" />

      {/* Agent list */}
      <div className="flex-1 overflow-y-auto pt-1">
        {loading && (
          <div className="px-4 py-6 text-[12px] text-text-muted text-center">Loading agents...</div>
        )}

        {!loading && agents.length === 0 && (
          <div className="px-4 py-6 text-[12px] text-text-muted text-center">No recent agents</div>
        )}

        {groups.map((group) => (
          <div key={group.label}>
            <div className="px-4 pt-3 pb-1">
              <span className="text-[11px] font-medium text-text-muted uppercase tracking-wider">{group.label}</span>
            </div>
            {group.agents.map((a) => {
              const isActive = a.id === activeId
              const label = a.name || a.summary?.slice(0, 40) || 'Untitled agent'
              const dotClass = STATUS_DOT[a.status] ?? 'bg-neutral-600'

              return (
                <button
                  key={a.id}
                  onClick={() => { onSelectHistory(a.id); onClose() }}
                  className={`
                    w-full text-left px-4 py-1.5 flex items-center gap-2
                    transition-colors cursor-pointer text-[13px] leading-snug
                    ${isActive
                      ? 'bg-white/[0.08] text-text'
                      : 'text-text-secondary hover:bg-white/[0.04] hover:text-text'
                    }
                  `}
                >
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotClass}`} />
                  <span className="truncate flex-1">{label}</span>
                  <span className="text-[10px] text-text-muted flex-shrink-0">{timeAgo(a.createdAt)}</span>
                </button>
              )
            })}
          </div>
        ))}
      </div>

      {/* Bottom controls */}
      <div className="border-t border-white/[0.06] px-3 py-2 flex items-center justify-between">
        {isRunning ? (
          <button
            onClick={onStop}
            className="text-[11px] text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-white/5 transition-colors cursor-pointer"
          >
            Stop Agent
          </button>
        ) : (
          <span className="text-[10px] text-text-muted">Agent Command</span>
        )}
        <button
          onClick={onLogout}
          className="text-text-muted hover:text-text-secondary p-1 rounded hover:bg-white/5 transition-colors cursor-pointer"
          title="Log out"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M6 2H3a1 1 0 00-1 1v10a1 1 0 001 1h3M11 11l3-3-3-3M14 8H6" />
          </svg>
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop: always visible */}
      <div className="hidden md:flex h-[100dvh] flex-shrink-0">
        {sidebar}
      </div>

      {/* Mobile: slide-over overlay */}
      {open && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={onClose}
          />
          <div className="relative h-full animate-slide-in">
            {sidebar}
          </div>
        </div>
      )}
    </>
  )
}
