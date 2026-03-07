import { useState } from 'react'
import Markdown from 'react-markdown'
import type { Message } from '../types'
import { agents } from '../agents'

interface Props {
  message: Message
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'
  const isThinking = message.type === 'thinking'
  const agent = agents.find((a) => a.id === message.agentId)

  if (isThinking) {
    return <ThinkingBlock content={message.content} agentLabel={agent?.label} />
  }

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-white/[0.07] flex items-center justify-center text-sm text-text-secondary flex-shrink-0 mt-0.5">
          {agent?.avatar ?? '◎'}
        </div>
      )}

      <div className={`min-w-0 ${isUser ? 'max-w-[72%]' : 'max-w-full'}`}>
        {!isUser && (
          <span className="text-[11px] text-text-muted font-medium uppercase tracking-wider mb-1 block">
            {agent?.label ?? 'Agent'}
          </span>
        )}

        <div
          className={`
            px-4 py-2.5 rounded-2xl text-[14.5px] leading-relaxed break-words
            ${isUser
              ? 'bg-user-bubble text-white rounded-br-md whitespace-pre-wrap'
              : 'bg-agent-bubble text-text'
            }
          `}
        >
          {isUser ? (
            message.content || <span className="text-text-muted italic">Waiting for agent...</span>
          ) : (
            <div className="prose-agent">
              <Markdown>{message.content}</Markdown>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 mt-1">
          <span className="text-[10px] text-text-muted">
            {formatTime(message.timestamp)}
          </span>
          {message.meta && (
            <span className="text-[10px] text-text-muted">
              {message.meta.split(' | ').map((link, i) => (
                <a
                  key={i}
                  href={link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 underline mr-2"
                >
                  {link.includes('pull') ? 'PR' : 'View Agent'}
                </a>
              ))}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

function ThinkingBlock({ content, agentLabel }: { content: string; agentLabel?: string }) {
  const [expanded, setExpanded] = useState(false)

  const preview = content.length > 120
    ? content.slice(0, 120).trimEnd() + '...'
    : content

  return (
    <div className="flex gap-3 justify-start">
      <div className="w-7 h-7 flex items-center justify-center flex-shrink-0 mt-0.5">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className="text-text-muted">
          <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 2" />
          <circle cx="8" cy="8" r="2" fill="currentColor" />
        </svg>
      </div>

      <button
        onClick={() => setExpanded(!expanded)}
        className="min-w-0 text-left cursor-pointer group"
      >
        <span className="text-[11px] text-text-muted font-medium uppercase tracking-wider mb-1 flex items-center gap-1.5">
          <span>{agentLabel ?? 'Agent'} — thinking</span>
          <svg
            width="10"
            height="10"
            viewBox="0 0 16 16"
            fill="none"
            className={`text-text-muted transition-transform duration-150 ${expanded ? 'rotate-180' : ''}`}
          >
            <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </span>

        <div
          className={`
            px-3 py-2 rounded-lg border border-white/[0.04] bg-white/[0.02]
            text-[13px] leading-relaxed text-text-muted whitespace-pre-wrap break-words
            font-mono transition-all duration-200
            ${expanded ? 'max-h-[600px] overflow-y-auto' : 'max-h-[3.5em] overflow-hidden'}
          `}
        >
          {expanded ? content : preview}
        </div>
      </button>
    </div>
  )
}

function formatTime(d: Date) {
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
