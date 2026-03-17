import { useState, useRef, useEffect, useCallback } from 'react'
import type { Message, Agent } from './types'
import { defaultAgent } from './agents'
import { launchAgent, followUp, pollStatus, stopAgent, getStoredKey, clearKey } from './api'
import AgentSidebar from './components/AgentSidebar'
import MessageBubble from './components/MessageBubble'
import TypingIndicator from './components/TypingIndicator'
import ChatInput from './components/ChatInput'
import LoginScreen from './components/LoginScreen'

let nextId = 0
function uid() {
  return String(++nextId)
}

const POLL_INTERVAL = 2500

function displayContent(role: 'user' | 'agent', text: string): string {
  if (role !== 'user') return text
  if (!text.includes('Read and adopt the full persona') || !text.includes('\n\n')) return text
  const idx = text.indexOf('\n\n')
  const after = text.slice(idx + 2).trim()
  return after || text
}

export default function App() {
  const [authed, setAuthed] = useState(() => !!getStoredKey())

  if (!authed) {
    return <LoginScreen onLogin={() => setAuthed(true)} />
  }

  return <ChatApp onLogout={() => { clearKey(); setAuthed(false) }} />
}

function ChatApp({ onLogout }: { onLogout: () => void }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [agentStatus, setAgentStatus] = useState<string | null>(null)
  const [agent, setAgent] = useState<Agent>(defaultAgent)
  const [cursorAgentId, setCursorAgentId] = useState<string | null>(null)
  const [mobileSidebar, setMobileSidebar] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const messageCountRef = useRef(0)

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(scrollToBottom, [messages, loading, scrollToBottom])

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [])

  function startPolling(agentId: string) {
    if (pollingRef.current) clearInterval(pollingRef.current)

    pollingRef.current = setInterval(async () => {
      try {
        const data = await pollStatus(agentId)
        setAgentStatus(data.status)

        if (data.messages && data.messages.length >= messageCountRef.current) {
          const next = data.messages.map((m: { id: string; type: string; text: string }) => {
            const role = m.type === 'user_message' ? ('user' as const) : ('agent' as const)
            return {
              id: m.id || uid(),
              role,
              type: m.type === 'assistant_message' ? 'assistant_message' : m.type === 'user_message' ? undefined : 'thinking',
              content: displayContent(role, m.text ?? ''),
              timestamp: new Date(),
              agentId: agent.id,
            }
          })
          messageCountRef.current = next.length
          setMessages(next)
        }

        const terminal = data.status === 'FINISHED' || data.status === 'STOPPED' || data.status === 'ERRORED'
        if (terminal) {
          if (pollingRef.current) clearInterval(pollingRef.current)
          pollingRef.current = null
          if (data.status === 'ERRORED') {
            setMessages((prev) => [
              ...prev,
              { id: uid(), role: 'agent', content: 'Agent encountered an error.', timestamp: new Date(), agentId: agent.id },
            ])
          }
          setLoading(false)
        }
      } catch {
        if (pollingRef.current) clearInterval(pollingRef.current)
        pollingRef.current = null
        setMessages((prev) => [
          ...prev,
          { id: uid(), role: 'agent', content: 'Lost connection to agent.', timestamp: new Date(), agentId: agent.id },
        ])
        setLoading(false)
      }
    }, POLL_INTERVAL)
  }

  async function handleSelectAgent(id: string) {
    if (pollingRef.current) clearInterval(pollingRef.current)
    pollingRef.current = null

    setCursorAgentId(id)
    setLoading(true)
    setMessages([])
    messageCountRef.current = 0
    setAgentStatus(null)

    try {
      const data = await pollStatus(id)
      setAgentStatus(data.status)

      if (data.messages && data.messages.length > 0) {
        const next = data.messages.map((m: { id: string; type: string; text: string }) => {
          const role = m.type === 'user_message' ? ('user' as const) : ('agent' as const)
          return {
            id: m.id || uid(),
            role,
            type: m.type === 'assistant_message' ? 'assistant_message' : m.type === 'user_message' ? undefined : 'thinking',
            content: displayContent(role, m.text ?? ''),
            timestamp: new Date(),
            agentId: agent.id,
          }
        })
        messageCountRef.current = next.length
        setMessages(next)
      }

      const isActive = data.status === 'RUNNING' || data.status === 'CREATING'
      if (isActive) {
        startPolling(id)
      } else {
        setLoading(false)
      }
    } catch {
      setMessages([
        { id: uid(), role: 'agent', content: 'Failed to load conversation.', timestamp: new Date(), agentId: agent.id },
      ])
      setLoading(false)
    }

  }

  async function handleSend(text: string) {
    const userMsg: Message = {
      id: uid(),
      role: 'user',
      content: text,
      timestamp: new Date(),
      agentId: agent.id,
    }
    setMessages((prev) => [...prev, userMsg])
    messageCountRef.current += 1
    setLoading(true)

    try {
      const data = cursorAgentId
        ? await followUp(text, agent.id, cursorAgentId)
        : await launchAgent(text, agent.id)

      if (!data.ok) {
        setMessages((prev) => [
          ...prev,
          { id: uid(), role: 'agent', content: data.message || 'Launch failed', timestamp: new Date(), agentId: agent.id },
        ])
        setLoading(false)
        return
      }

      const newId = data.cursor_agent_id!
      setCursorAgentId(newId)
      setAgentStatus(data.status)

      startPolling(newId)
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: 'agent',
          content: `Error: ${err instanceof Error ? err.message : 'Something went wrong'}`,
          timestamp: new Date(),
          agentId: agent.id,
        },
      ])
      setLoading(false)
    }
  }

  function handleClear() {
    if (pollingRef.current) clearInterval(pollingRef.current)
    pollingRef.current = null
    messageCountRef.current = 0
    setMessages([])
    setCursorAgentId(null)
    setAgentStatus(null)
    setLoading(false)
  }

  async function handleStop() {
    if (cursorAgentId) {
      await stopAgent(cursorAgentId)
    }
    if (pollingRef.current) clearInterval(pollingRef.current)
    pollingRef.current = null
    setLoading(false)
    setAgentStatus('STOPPED')
    setCursorAgentId(null)
  }

  const hasMessages = messages.length > 0
  const isRunning = agentStatus === 'RUNNING' || agentStatus === 'CREATING'
  const isEnded = agentStatus === 'STOPPED' || agentStatus === 'ERRORED' || agentStatus === 'TIMEOUT'
  const inputDisabled = loading

  const statusLabel: Record<string, string> = {
    STOPPED: 'Agent was stopped.',
    ERRORED: 'Agent encountered an error.',
    TIMEOUT: 'Agent timed out.',
  }

  return (
    <div className="h-screen flex flex-row">
      <AgentSidebar
        open={mobileSidebar}
        onClose={() => setMobileSidebar(false)}
        activeId={cursorAgentId}
        selectedAgent={agent}
        onSelectAgent={setAgent}
        onSelectHistory={handleSelectAgent}
        onNew={handleClear}
        onLogout={onLogout}
        isRunning={isRunning}
        onStop={handleStop}
      />

      <div className="flex-1 flex flex-col min-w-0 bg-bg">
        {/* Top bar */}
        <header className="flex-shrink-0 border-b border-border px-4 md:px-6 py-2.5 flex items-center gap-3">
          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileSidebar(true)}
            className="md:hidden text-text-muted hover:text-text p-1 -ml-1 rounded hover:bg-white/5 transition-colors cursor-pointer"
          >
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M2 4h12M2 8h12M2 12h12" />
            </svg>
          </button>
          <div className={`w-2 h-2 rounded-full ${
            isRunning ? 'bg-blue-400 animate-pulse' :
            isEnded ? 'bg-red-400' :
            cursorAgentId ? 'bg-green-500' : 'bg-neutral-600'
          }`} />
          <span className="text-[13px] text-text-secondary truncate">
            {cursorAgentId
              ? <>{agent.label} <span className="text-text-muted font-mono text-[11px] ml-1">{agentStatus}</span></>
              : agent.label
            }
          </span>
        </header>

        {/* Chat area */}
        <main className="flex-1 overflow-y-auto">
          {!hasMessages && !loading ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md px-6">
                <div className="text-4xl mb-4">{agent.avatar}</div>
                <h2 className="text-lg font-medium text-text mb-1">{agent.label}</h2>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {agent.description}. Send a prompt to launch a cloud agent.
                </p>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto px-4 md:px-6 py-4 md:py-6 flex flex-col gap-3 md:gap-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {loading && <TypingIndicator />}

              {isEnded && (
                <div className="flex flex-col items-center gap-3 py-4 mt-2">
                  <div className="flex items-center gap-2 text-sm text-text-secondary">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className={agentStatus === 'ERRORED' ? 'text-red-400' : 'text-text-muted'}>
                      <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                      <path d="M8 5V9M8 11V11.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                    <span>{statusLabel[agentStatus!] ?? 'Conversation ended.'}</span>
                  </div>
                  <button
                    onClick={handleClear}
                    className="
                      px-4 py-2 rounded-lg text-sm font-medium
                      bg-white/10 text-white hover:bg-white/15
                      transition-colors cursor-pointer
                    "
                  >
                    New Conversation
                  </button>
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          )}
        </main>

        {/* Input bar */}
        <footer className="flex-shrink-0 border-t border-border">
          <div className="max-w-3xl mx-auto px-4 md:px-6 py-3">
            <ChatInput onSend={handleSend} disabled={inputDisabled} />
          </div>
        </footer>
      </div>
    </div>
  )
}
