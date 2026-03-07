import { useState, useEffect } from 'react'

export default function TypingIndicator() {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(t)
  }, [])

  const fmt = elapsed < 60 ? `${elapsed}s` : `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`

  return (
    <div className="flex gap-3 items-start">
      <div className="w-7 h-7 rounded-full bg-white/[0.07] flex items-center justify-center flex-shrink-0">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className="text-text-muted animate-spin" style={{ animationDuration: '2s' }}>
          <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 2" />
          <circle cx="8" cy="8" r="2" fill="currentColor" />
        </svg>
      </div>
      <div className="flex flex-col gap-1 pt-1">
        <span className="text-[11px] text-text-muted font-medium uppercase tracking-wider">
          Agent is thinking... <span className="font-mono text-text-secondary">{fmt}</span>
        </span>
        <div className="flex gap-1 items-center">
          <span className="w-1.5 h-1.5 rounded-full bg-text-muted animate-bounce [animation-delay:0ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-text-muted animate-bounce [animation-delay:150ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-text-muted animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  )
}
