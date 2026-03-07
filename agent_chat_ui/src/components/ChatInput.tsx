import { useState, useRef, useEffect } from 'react'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!disabled) ref.current?.focus()
  }, [disabled])

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function submit() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
    if (ref.current) ref.current.style.height = 'auto'
  }

  function autoResize() {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  return (
    <div className="relative">
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => {
          setValue(e.target.value)
          autoResize()
        }}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        rows={1}
        placeholder="Send a message..."
        className="
          w-full resize-none bg-surface border border-border rounded-xl
          px-4 py-3 pr-14 text-[14.5px] text-text placeholder:text-text-muted
          focus:outline-none focus:border-border-focus
          transition-colors duration-150
          disabled:opacity-50 font-[inherit]
        "
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        aria-label="Send"
        className="
          absolute right-2.5 bottom-2.5
          w-8 h-8 flex items-center justify-center rounded-lg
          bg-white text-black
          disabled:opacity-20 disabled:cursor-default
          hover:bg-white/90 transition-all duration-150
          cursor-pointer
        "
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 2L8 14M8 2L3 7M8 2L13 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
    </div>
  )
}
