import { useState, useRef, useEffect, useCallback } from 'react'
import type { Message, Agent } from './types'
import { defaultAgent } from './agents'
import { streamChat, getConversation, getStoredKey, clearKey } from './api'
import { agents as agentPresets } from './agents'
import AgentSidebar from './components/AgentSidebar'
import MessageBubble from './components/MessageBubble'
import TypingIndicator from './components/TypingIndicator'
import ChatInput from './components/ChatInput'
import LoginScreen from './components/LoginScreen'

let nextId = 0
function uid() {
  return String(++nextId)
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
  const [loadingReason, setLoadingReason] = useState<'history' | 'thinking'>('thinking')
  const [agent, setAgent] = useState<Agent>(defaultAgent)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [mobileSidebar, setMobileSidebar] = useState(false)
  const [sidebarRefresh, setSidebarRefresh] = useState(0)
  const bottomRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  // Tracks the streaming assistant message being built token-by-token
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null)
  // Track if onDone has already fired for the current stream
  const doneRef = useRef(false)

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(scrollToBottom, [messages, loading, scrollToBottom])

  // Cleanup abort on unmount
  useEffect(() => {
    return () => { abortRef.current?.abort() }
  }, [])

  function handleSend(text: string) {
    // Add user message
    const userMsg: Message = {
      id: uid(),
      role: 'user',
      content: text,
      timestamp: new Date(),
      agentId: agent.id,
    }
    setMessages((prev) => [...prev, userMsg])
    setLoadingReason('thinking')
    setLoading(true)

    // Prepare abort controller
    abortRef.current?.abort()
    const abort = new AbortController()
    abortRef.current = abort
    doneRef.current = false

    // Prepare a message ID for the streaming assistant response
    const assistantMsgId = uid()
    setStreamingMsgId(assistantMsgId)
    let thinkingMsgId: string | null = null

    streamChat(conversationId, text, agent.id, {
      onConversationId: (id, agentId) => {
        setConversationId(id)
        // Resolve persona from server response
        if (agentId) {
          const match = agentPresets.find((a) => a.id === agentId)
          if (match) setAgent(match)
        }
      },
      onToken: (token) => {
        setMessages((prev) => {
          const existing = prev.find((m) => m.id === assistantMsgId)
          if (existing) {
            return prev.map((m) =>
              m.id === assistantMsgId ? { ...m, content: m.content + token } : m,
            )
          }
          // First token — create the assistant message
          return [
            ...prev,
            {
              id: assistantMsgId,
              role: 'assistant' as const,
              content: token,
              timestamp: new Date(),
              agentId: agent.id,
            },
          ]
        })
      },
      onThinking: (token) => {
        if (!thinkingMsgId) {
          thinkingMsgId = uid()
          setMessages((prev) => [
            ...prev,
            {
              id: thinkingMsgId!,
              role: 'assistant' as const,
              type: 'thinking' as const,
              content: token,
              timestamp: new Date(),
              agentId: agent.id,
            },
          ])
        } else {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === thinkingMsgId ? { ...m, content: m.content + token } : m,
            ),
          )
        }
      },
      onToolUse: () => {
        // Could show tool activity in UI — for now just keep loading state
      },
      onToolResult: () => {
        // Tool results feed back into Claude — nothing to show yet
      },
      onDone: () => {
        if (doneRef.current) return
        doneRef.current = true
        setStreamingMsgId(null)
        setLoading(false)
        setSidebarRefresh((n) => n + 1)
      },
      onError: (err) => {
        if (doneRef.current) return
        doneRef.current = true
        setStreamingMsgId(null)
        setMessages((prev) => [
          ...prev,
          {
            id: uid(),
            role: 'assistant',
            content: `Error: ${err.message}`,
            timestamp: new Date(),
            agentId: agent.id,
          },
        ])
        setLoading(false)
      },
    }, abort.signal)
  }

  async function handleSelectConversation(id: string) {
    abortRef.current?.abort()
    abortRef.current = null
    setStreamingMsgId(null)

    setConversationId(id)
    setLoadingReason('history')
    setLoading(true)
    setMessages([])

    try {
      const data = await getConversation(id)

      // Set persona from conversation data
      const match = agentPresets.find((a) => a.id === data.agentId)
      if (match) setAgent(match)

      if (data.messages && data.messages.length > 0) {
        const next = data.messages.map((m) => ({
          id: m.id || uid(),
          role: m.role,
          type: m.type,
          content: m.text,
          timestamp: new Date(m.createdAt),
          agentId: data.agentId,
        }))
        setMessages(next)
      }

      setLoading(false)
    } catch {
      setMessages([
        { id: uid(), role: 'assistant', content: 'Failed to load conversation.', timestamp: new Date(), agentId: agent.id },
      ])
      setLoading(false)
    }
  }

  function handleClear() {
    abortRef.current?.abort()
    abortRef.current = null
    setStreamingMsgId(null)
    setMessages([])
    setConversationId(null)
    setLoading(false)
  }

  function handleStop() {
    abortRef.current?.abort()
    abortRef.current = null
    setStreamingMsgId(null)
    setLoading(false)
  }

  const hasMessages = messages.length > 0
  const isStreaming = loading && loadingReason === 'thinking'
  const inputDisabled = loading

  return (
    <div className="h-[100dvh] flex flex-row">
      <AgentSidebar
        open={mobileSidebar}
        onClose={() => setMobileSidebar(false)}
        activeId={conversationId}
        selectedAgent={agent}
        onSelectAgent={setAgent}
        onSelectHistory={handleSelectConversation}
        onNew={handleClear}
        onLogout={onLogout}
        isRunning={isStreaming}
        onStop={handleStop}
        refreshKey={sidebarRefresh}
      />

      <div className="flex-1 flex flex-col min-w-0 bg-bg">
        {/* Top bar */}
        <header className="flex-shrink-0 border-b border-border px-4 md:px-6 pt-[max(0.625rem,env(safe-area-inset-top))] pb-2.5 flex items-center gap-3">
          <button
            onClick={() => setMobileSidebar(true)}
            className="md:hidden text-text-muted hover:text-text p-1 -ml-1 rounded hover:bg-white/5 transition-colors cursor-pointer"
          >
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M2 4h12M2 8h12M2 12h12" />
            </svg>
          </button>
          <div className={`w-2 h-2 rounded-full ${
            isStreaming ? 'bg-blue-400 animate-pulse' :
            conversationId ? 'bg-green-500' : 'bg-neutral-600'
          }`} />
          <span className="text-[13px] text-text-secondary truncate">
            {agent.label}
            {isStreaming && (
              <span className="text-blue-400/70 text-[11px] ml-1.5">streaming...</span>
            )}
          </span>
        </header>

        {!hasMessages && !loading ? (
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex-1" />
            <div className="px-4 md:px-6 pb-2">
              <div className="text-center max-w-md mx-auto mb-8">
                <div className="text-4xl mb-3">{agent.avatar}</div>
                <h2 className="text-lg font-medium text-text mb-1">{agent.label}</h2>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {agent.description}. Send a prompt to start a conversation.
                </p>
              </div>
              <div className="max-w-3xl mx-auto pb-[env(safe-area-inset-bottom)]">
                <ChatInput onSend={handleSend} disabled={inputDisabled} />
              </div>
            </div>
            <div className="flex-1" />
          </div>
        ) : (
          <>
            <main className="flex-1 overflow-y-auto min-h-0">
              <div className="max-w-3xl mx-auto px-4 md:px-6 pt-5 pb-4 md:py-6 flex flex-col gap-5 md:gap-6">
                {messages.map((msg) => (
                  <MessageBubble
                    key={msg.id}
                    message={msg}
                    streaming={msg.id === streamingMsgId}
                  />
                ))}
                {loading && loadingReason === 'thinking' && !messages.some((m) => m.id === streamingMsgId) && (
                  <TypingIndicator label="Agent is thinking" />
                )}
                {loading && loadingReason === 'history' && (
                  <TypingIndicator label="Loading conversation" />
                )}
                <div ref={bottomRef} />
              </div>
            </main>

            <footer className="flex-shrink-0 bg-bg/80 backdrop-blur-xl border-t border-white/[0.06] pb-[env(safe-area-inset-bottom)]">
              <div className="max-w-3xl mx-auto px-4 md:px-6 py-2">
                <ChatInput onSend={handleSend} disabled={inputDisabled} />
              </div>
            </footer>
          </>
        )}
      </div>
    </div>
  )
}
