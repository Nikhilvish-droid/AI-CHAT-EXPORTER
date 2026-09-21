const CONTEXT_TAGS = [
  'Previous decisions',
  'Current problem',
  'Technical context',
  'Previous solutions',
  'Important constraints',
]

const DOCS = [
  ['architecture.pdf', false],
  ['dataset.csv', false],
  ['design.png', true],
]

function CheckIcon({ className }) {
  return (
    <svg viewBox="0 0 12 12" className={className} aria-hidden="true">
      <path
        d="M2.5 6.2 4.7 8.5 9.5 3.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function WarnIcon({ className }) {
  return (
    <svg viewBox="0 0 12 12" className={className} aria-hidden="true">
      <path
        d="M6 1.6 11 10.4H1Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
      <path d="M6 5v2.3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <circle cx="6" cy="8.9" r="0.7" fill="currentColor" />
    </svg>
  )
}

function DocIcon() {
  return (
    <svg viewBox="0 0 14 16" className="hiw-i" aria-hidden="true">
      <path
        d="M2 1.5h6l4 4v9a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1Z"
        fill="currentColor"
        opacity="0.18"
      />
      <path
        d="M2 1.5h6l4 4v9a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1ZM8 1.5v4h4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function Step4Visual() {
  return (
    <div className="hiw-mock hiw-mock--agent" aria-hidden="true">
      <div className="hiw-agent-grid">
        <div className="hiw-agent-chat">
          <div className="hiw-mock-bar hiw-mock-bar--tight">
            <span className="hiw-mock-dots">
              <i />
              <i />
              <i />
            </span>
            <span className="hiw-mock-title">NEW AI CHAT</span>
          </div>

          <div className="hiw-pdf-chip">
            <DocIcon />
            <span className="hiw-pdf-name">memory-export.pdf</span>
            <span className="hiw-pdf-state">
              <CheckIcon className="hiw-i-xs" />
              LOADED
            </span>
          </div>

          <span className="hiw-mini-cap">CONTEXT RESTORED</span>
          <div className="hiw-tags">
            {CONTEXT_TAGS.map((tag) => (
              <span className="hiw-tag" key={tag}>
                <CheckIcon className="hiw-i-xs" />
                {tag}
              </span>
            ))}
          </div>
        </div>

        <div className="hiw-doc-table">
          <span className="hiw-mini-cap hiw-mini-cap--warn">MISSING DOCUMENTS</span>
          <div className="hiw-table">
            {DOCS.map(([name, available]) => (
              <div className="hiw-tr" key={name}>
                <span className="hiw-td-name">{name}</span>
                <span className={`hiw-badge ${available ? 'hiw-badge--ok' : 'hiw-badge--warn'}`}>
                  {available ? <CheckIcon className="hiw-i-xs" /> : <WarnIcon className="hiw-i-xs" />}
                  {available ? 'Available' : 'Missing'}
                </span>
              </div>
            ))}
          </div>
          <span className="hiw-attach">
            <svg viewBox="0 0 12 12" className="hiw-i-xs" aria-hidden="true">
              <path
                d="M6 2.4v7.2M2.4 6h7.2"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            ATTACH MISSING FILES
          </span>
        </div>
      </div>

      <div className="hiw-agent-ask">
        <span className="hiw-agent-avatar">AI</span>
        <p>Some referenced documents are missing. Please provide them to continue accurately.</p>
        <span className="hiw-caret hiw-caret--ask" />
      </div>
    </div>
  )
}
