import { useState, useEffect } from 'react'

interface Props {
  label?: string
}

export default function TypingIndicator({ label = 'Thinking' }: Props) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(t)
  }, [])

  const fmt = elapsed < 60 ? `${elapsed}s` : `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`

  return (
    <div className="flex gap-3 items-start">
      <div className="w-7 h-7 rounded-full bg-white/[0.06] border border-white/[0.06] flex items-center justify-center flex-shrink-0">
        <div className="w-3 h-3 rounded-full border-2 border-text-muted border-t-transparent animate-spin" />
      </div>
      <div className="flex flex-col gap-1.5 pt-0.5">
        <span className="text-[11px] text-text-muted font-medium tracking-wide">
          {label} <span className="text-text-muted/60 font-mono ml-0.5">{fmt}</span>
        </span>
        <div className="flex gap-[5px] items-center h-4">
          <span className="typing-dot w-[5px] h-[5px] rounded-full bg-text-muted/60" style={{ animationDelay: '0ms' }} />
          <span className="typing-dot w-[5px] h-[5px] rounded-full bg-text-muted/60" style={{ animationDelay: '160ms' }} />
          <span className="typing-dot w-[5px] h-[5px] rounded-full bg-text-muted/60" style={{ animationDelay: '320ms' }} />
        </div>
      </div>
    </div>
  )
}
