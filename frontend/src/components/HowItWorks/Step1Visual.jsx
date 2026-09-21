function LinkIcon() {
  return (
    <svg viewBox="0 0 16 16" className="hiw-s1-icon" aria-hidden="true">
      <path
        d="M6.5 9.5a2.8 2.8 0 0 0 4 0l2-2a2.83 2.83 0 0 0-4-4l-1 1M9.5 6.5a2.8 2.8 0 0 0-4 0l-2 2a2.83 2.83 0 0 0 4 4l1-1"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg viewBox="0 0 16 16" className="hiw-s1-icon hiw-s1-icon--btn" aria-hidden="true">
      <path
        d="M3 8h9M8.5 4.5 12 8l-3.5 3.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 16 16" className="hiw-s1-icon hiw-s1-icon--status" aria-hidden="true">
      <path
        d="m3.5 8.2 3 3 6-6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function Step1Visual() {
  return (
    <div className="hiw-mock hiw-s1" aria-hidden="true">
      {/* AREA 1 — conversation preview */}
      <div className="hiw-s1-convo">
        <div className="hiw-s1-convo-bar">
          <span className="hiw-s1-dots">
            <i />
            <i />
            <i />
          </span>
          <span className="hiw-s1-convo-title">PREVIOUS AI CONVERSATION</span>
          <span className="hiw-s1-convo-tag">PUBLIC</span>
        </div>

        <div className="hiw-s1-convo-body">
          <div className="hiw-s1-msg hiw-s1-msg--user">
            <span className="hiw-s1-msg-who">YOU</span>
            <p>I need to build a RAG pipeline...</p>
          </div>

          <div className="hiw-s1-msg hiw-s1-msg--ai">
            <span className="hiw-s1-msg-who">AI AGENT</span>
            <p>Start with chunking, embeddings...</p>
          </div>

          <div className="hiw-s1-meta">
            <span>24 MESSAGES</span>
            <span className="hiw-s1-meta-sep" />
            <span>6 DECISIONS</span>
            <span className="hiw-s1-meta-sep" />
            <span>3 IMAGES</span>
          </div>
        </div>
      </div>

      {/* AREA 2 — link submission */}
      <div className="hiw-s1-link">
        <span className="hiw-s1-link-label">PUBLIC CONVERSATION LINK</span>

        <div className="hiw-s1-link-row">
          <span className="hiw-s1-link-field">
            <LinkIcon />
            <span>chat.../share/a8f2c1</span>
          </span>

          <span className="hiw-s1-submit-btn">
            SUBMIT CHAT
            <SendIcon />
          </span>
        </div>
      </div>

      {/* AREA 3 — status */}
      <div className="hiw-s1-status">
        <span className="hiw-s1-status-icon">
          <CheckIcon />
        </span>
        <span className="hiw-s1-status-text">
          <strong>PUBLIC LINK READY</strong>
          <span>Conversation ready to be imported</span>
        </span>
      </div>

      {/* decorative particles */}
      <span className="hiw-s1-spark hiw-s1-spark--1" />
      <span className="hiw-s1-spark hiw-s1-spark--2" />
      <span className="hiw-s1-spark hiw-s1-spark--3" />
    </div>
  )
}
