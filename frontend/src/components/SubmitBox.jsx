import { useMemo, useState } from 'react'
import { convertConversation } from '../api'

// Mirrors backend/app/routers/conversation.py::ALLOWED_HOSTS so bad links
// never leave the browser. Keep this list in sync with the 
const PLATFORMS = [
  { key: 'chatgpt', label: 'ChatGPT', color: '#74e0c4', hosts: ['chatgpt.com', 'chat.openai.com'] },
  { key: 'gemini', label: 'Gemini', color: '#8ab4ff', hosts: ['gemini.google.com', 'share.gemini.google', 'g.co'] },
  { key: 'claude', label: 'Claude', color: '#e8a37c', hosts: ['claude.ai'] },
]

// One label per backend call in convertConversation() (src/api.js):
// scrape -> analyze -> write -> export.
const STAGE_LABELS = [
  'Reading the conversation…',
  'Finding what matters…',
  'Writing the sections…',
  'Binding the PDF…',
]

// Share sheets often copy a sentence around the link ("Check out this chat:
// https://g.co/…"), which would fail URL parsing. Read just the link out of
// whatever is in the box — the input itself is left to the browser so native
// copy/paste behaves normally.
function extractUrl(text) {
  const match = text.match(/https?:\/\/[^\s<>"']+/i)
  return match ? match[0] : text.trim()
}

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
 * actual product entry point. Submitting a link runs the real backend
 * pipeline (see convertConversation in src/api.js), one stage per request,
 * and ends with the generated PDF ready to download.
 */
export default function SubmitBox() {
  const [value, setValue] = useState('')
  const [status, setStatus] = useState('idle') // idle | invalid | loading | success
  const [stageIndex, setStageIndex] = useState(0)
  const [receipt, setReceipt] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [downloadUrl, setDownloadUrl] = useState(null)

  const link = useMemo(() => extractUrl(value), [value])
  const platform = useMemo(() => detectPlatform(link), [link])

  const releaseDownload = () => {
    setDownloadUrl((current) => {
      if (current) URL.revokeObjectURL(current)
      return null
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
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
    setStatus('loading')
    setStageIndex(0)

    try {
      const result = await convertConversation(link, setStageIndex)
      releaseDownload()
      setDownloadUrl(URL.createObjectURL(result.blob))
      setReceipt({
        platform: platform.label,
        filename: result.filename,
        codeBlocks: result.codeBlocks,
        images: result.imagesEmbedded,
        missing: result.filesMissing,
      })
      setStatus('success')
    } catch (err) {
      setStatus('invalid')
      setErrorMessage(err.message || 'Something went wrong. Please try again.')
    }
  }

  const reset = () => {
    releaseDownload()
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
            <a
              href={downloadUrl}
              download={receipt.filename}
              className="submit-btn submit-btn--primary"
            >
              Download PDF
            </a>
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
