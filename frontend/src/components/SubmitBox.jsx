import { useMemo, useRef, useState } from 'react'

// Mirrors backend/app/routers/conversation.py::ALLOWED_HOSTS so bad links
// never leave the browser. Keep this list in sync with the backend.
const PLATFORMS = [
  { key: 'chatgpt', label: 'ChatGPT', color: '#74e0c4', hosts: ['chatgpt.com', 'chat.openai.com'] },
  { key: 'gemini', label: 'Gemini', color: '#8ab4ff', hosts: ['gemini.google.com', 'share.gemini.google', 'g.co'] },
  { key: 'claude', label: 'Claude', color: '#e8a37c', hosts: ['claude.ai'] },
]

const STAGE_LABELS = [
  'Reading the conversation…',
  'Finding what matters…',
  'Writing the sections…',
  'Binding the PDF…',
]

function detectPlatform(url) {
  if (!url || !url.trim()) return null
  let host = ''
  try {
    host = new URL(url.trim()).hostname.toLowerCase().replace(/^www\./, '')
  } catch {
    return undefined
  }
  for (const p of PLATFORMS) {
    if (p.hosts.some((h) => host === h || host.endsWith(`.${h}`))) return p
  }
  return null
}

/**
 * The box the figure "holds" at the end of the cave reveal — this is the
 * actual product entry point. Demo-only submit for now (see
 * runDemoSubmit): swap it for a real `fetch('/submit-link', ...)` call
 * against backend/app/routers/conversation.py when wiring the backend up;
 * everything else (chip, spinner, receipt, errors) keeps working as-is.
 */
export default function SubmitBox() {
  const [value, setValue] = useState('')
  const [status, setStatus] = useState('idle') // idle | invalid | loading | success
  const [stageIndex, setStageIndex] = useState(0)
  const [receipt, setReceipt] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')
  const timers = useRef([])

  const platform = useMemo(() => detectPlatform(value), [value])

  const clearTimers = () => {
    timers.current.forEach(clearTimeout)
    timers.current = []
  }

  const runDemoSubmit = () => {
    setStatus('loading')
    setStageIndex(0)
    STAGE_LABELS.forEach((_, i) => {
      if (i === 0) return
      timers.current.push(setTimeout(() => setStageIndex(i), i * 900))
    })
    timers.current.push(
      setTimeout(() => {
        setStatus('success')
        setReceipt({ platform: platform.label, codeBlocks: 12, images: 3, missing: 1 })
      }, STAGE_LABELS.length * 900 + 350),
    )
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    clearTimers()
    if (!value.trim()) {
      setStatus('invalid')
      setErrorMessage('Paste a share link to get started.')
      return
    }
    if (!platform) {
      setStatus('invalid')
      setErrorMessage("That doesn't look like a supported share link.")
      return
    }
    setErrorMessage('')
    runDemoSubmit()
  }

  const reset = () => {
    clearTimers()
    setStatus('idle')
    setReceipt(null)
    setValue('')
  }

  const isLoading = status === 'loading'
  const isInvalid = status === 'invalid'

  return (
    <div className="submit-box">
      {status === 'success' ? (
        <div className="submit-receipt">
          <div className="submit-receipt-check">✓</div>
          <p className="submit-receipt-title">Memory file ready.</p>
          <p className="submit-receipt-meta">
            {receipt.codeBlocks} code blocks · {receipt.images} images embedded
          </p>
          <div className="submit-receipt-actions">
            <button type="button" className="submit-btn submit-btn--primary" disabled>
              Download PDF
            </button>
            <button type="button" className="submit-btn submit-btn--ghost" onClick={reset}>
              Convert another
            </button>
          </div>
        </div>
      ) : (
        <form className="submit-form" onSubmit={handleSubmit}>
          <p className="submit-label">Drop your share link</p>
          <div
            className={`submit-shell ${isInvalid ? 'submit-shell--invalid' : ''} ${
              isLoading ? 'submit-shell--loading' : ''
            }`}
            style={platform ? { '--platform-color': platform.color } : undefined}
          >
            <input
              type="text"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              placeholder="ChatGPT, Gemini or Claude…"
              value={value}
              disabled={isLoading}
              onChange={(e) => {
                setValue(e.target.value)
                if (status === 'invalid') setStatus('idle')
              }}
            />  
            <button type="submit" className="submit-go" disabled={isLoading} aria-label="Generate memory PDF">
              {isLoading ? <span className="submit-spinner" aria-hidden="true" /> : '→'}
            </button>
          </div>

          <div className="submit-footline">
            {isLoading ? (
              <span className="submit-stage">{STAGE_LABELS[stageIndex]}</span>
            ) : isInvalid ? (
              <span className="submit-error">{errorMessage}</span>
            ) : platform ? (
              <span className="submit-detected">{platform.label} detected ✓</span>
            ) : (
              <span className="submit-hint">Your chat context, as a PDF - Continue where you left off.</span>
            )}
          </div>
        </form>
      )}
    </div>
  )
}
