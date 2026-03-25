import { useState, useRef, useEffect } from 'react'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('')
  const [focused, setFocused] = useState(false)
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

  const canSend = !!value.trim() && !disabled

  return (
    <div
      className={`
        relative flex items-end gap-0
        bg-surface rounded-2xl border transition-all duration-200
        ${focused ? 'border-white/20 shadow-[0_0_0_1px_rgba(255,255,255,0.08),0_2px_12px_rgba(0,0,0,0.4)]' : 'border-border'}
        ${disabled ? 'opacity-60' : ''}
      `}
    >
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => {
          setValue(e.target.value)
          autoResize()
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        rows={1}
        placeholder="Message..."
        className="
          flex-1 resize-none bg-transparent
          pl-4 pr-2 py-3 text-[16px] md:text-[14px] text-text placeholder:text-text-muted
          focus:outline-none
          disabled:cursor-default font-[inherit]
          leading-[1.5]
        "
      />
      <div className="pr-2 pb-2 pt-1 flex-shrink-0">
        <button
          onClick={submit}
          disabled={!canSend}
          aria-label="Send"
          className={`
            w-8 h-8 flex items-center justify-center rounded-full
            transition-all duration-200 cursor-pointer
            ${canSend
              ? 'bg-white text-black hover:bg-white/90 scale-100'
              : 'bg-white/10 text-text-muted scale-95 cursor-default'
            }
          `}
        >
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
            <path d="M8 13V3M8 3L4 7M8 3L12 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
  )
}
