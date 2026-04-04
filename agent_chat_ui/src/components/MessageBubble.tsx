import { useState } from 'react'
import Markdown from 'react-markdown'
import type { Message } from '../types'
import { agents } from '../agents'

interface Props {
  message: Message
  streaming?: boolean
}

export default function MessageBubble({ message, streaming }: Props) {
  const isUser = message.role === 'user'
  const isThinking = message.type === 'thinking'
  const agent = agents.find((a) => a.id === message.agentId)

  if (isThinking) {
    return <ThinkingBlock content={message.content} agentLabel={agent?.label} />
  }

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[78%] md:max-w-[65%]">
          <div className="
            px-4 py-2.5 rounded-[20px] rounded-br-md
            bg-white/[0.12] text-text text-[14px] leading-relaxed
            whitespace-pre-wrap break-words
          ">
            {message.content || <span className="text-text-muted italic">Waiting for agent...</span>}
          </div>
          <div className="text-right mt-1 pr-1">
            <span className="text-[10px] text-text-muted/70">{formatTime(message.timestamp)}</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3 items-start">
      <div className="w-7 h-7 rounded-full bg-white/[0.06] border border-white/[0.06] flex items-center justify-center text-[13px] flex-shrink-0 mt-0.5">
        {agent?.avatar ?? '◎'}
      </div>

      <div className="min-w-0 flex-1 max-w-[calc(100%-3rem)]">
        <span className="text-[11px] text-text-muted font-medium tracking-wide mb-1.5 block">
          {agent?.label ?? 'Agent'}
        </span>

        <div className="text-[14px] leading-[1.7] text-text">
          <div className="prose-agent">
            <Markdown>{message.content}</Markdown>
            {streaming && <span className="inline-block w-[2px] h-[1em] bg-blue-400 animate-pulse align-text-bottom ml-0.5" />}
          </div>
        </div>

        <div className="flex items-center gap-3 mt-2">
          <span className="text-[10px] text-text-muted/70">{formatTime(message.timestamp)}</span>
          {message.meta && (
            <span className="text-[10px]">
              {message.meta.split(' | ').map((link, i) => (
                <a
                  key={i}
                  href={link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400/80 hover:text-blue-400 underline underline-offset-2 mr-2"
                >
                  {link.includes('pull') ? 'PR' : 'View'}
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
    <div className="flex gap-3 items-start">
      <div className="w-7 h-7 flex items-center justify-center flex-shrink-0 mt-0.5">
        <div className="w-5 h-5 rounded-full border border-white/10 flex items-center justify-center">
          <div className="w-1.5 h-1.5 rounded-full bg-text-muted" />
        </div>
      </div>

      <button
        onClick={() => setExpanded(!expanded)}
        className="min-w-0 text-left cursor-pointer group"
      >
        <span className="text-[11px] text-text-muted font-medium tracking-wide mb-1.5 flex items-center gap-1.5">
          <span>{agentLabel ?? 'Agent'} thinking</span>
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
            px-3 py-2 rounded-xl border border-white/[0.05] bg-white/[0.02]
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
