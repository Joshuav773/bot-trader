import { useState } from 'react'
import { authenticate } from '../api'

interface Props {
  onLogin: () => void
}

export default function LoginScreen({ onLogin }: Props) {
  const [key, setKey] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!key.trim()) return

    setLoading(true)
    setError('')

    const ok = await authenticate(key.trim())
    if (ok) {
      onLogin()
    } else {
      setError('Invalid API key')
    }
    setLoading(false)
  }

  return (
    <div className="h-[100dvh] flex items-center justify-center bg-bg">
      <form onSubmit={handleSubmit} className="w-full max-w-sm px-6">
        <div className="text-center mb-8">
          <div className="text-3xl mb-3">◈</div>
          <h1 className="text-xl font-semibold tracking-tight text-text">Agent Command</h1>
          <p className="text-sm text-text-secondary mt-1">Enter your API key to continue</p>
        </div>

        <input
          type="password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="API key"
          autoFocus
          className="
            w-full bg-surface border border-border rounded-xl
            px-4 py-3 text-[14.5px] text-text placeholder:text-text-muted
            focus:outline-none focus:border-border-focus
            transition-colors duration-150 font-mono
          "
        />

        {error && (
          <p className="text-red-400 text-sm mt-2">{error}</p>
        )}

        <button
          type="submit"
          disabled={loading || !key.trim()}
          className="
            w-full mt-4 py-3 rounded-xl text-sm font-medium
            bg-white text-black hover:bg-white/90
            disabled:opacity-30 disabled:cursor-default
            transition-all duration-150 cursor-pointer
          "
        >
          {loading ? 'Verifying...' : 'Continue'}
        </button>
      </form>
    </div>
  )
}
