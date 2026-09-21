const AGENTS = [
  {
    key: 'chatgpt',
    image: '/agents/chatgpt.png',
    maker: 'OpenAI',
    blurb: 'Paste a shared chat link and export it straight into a memory PDF.',
  },
  {
    key: 'claude',
    image: '/agents/claude.png',
    maker: 'Anthropic',
    blurb: 'Works with shared Claude conversations, code and all.',
  },
  {
    key: 'gemini',
    image: '/agents/gemini.png',
    maker: 'Google',
    blurb: 'Turn a shared Gemini chat into structured, portable context.',
  },
]

export default function SupportedAgents() {
  return (
    <section className="agents-section" aria-labelledby="agents-heading">
      <div className="agents-inner">
        <header className="agents-head">
          <span className="agents-eyebrow">WORKS WITH</span>
          <h2 id="agents-heading">Submit a chat from any of these agents.</h2>
          <p>
            Drop in a shared conversation link from any of the AI agents below and we&apos;ll turn
            it into a memory PDF your next agent can read.
          </p>
        </header>

        <ul className="agents-grid">
          {AGENTS.map((agent) => (
            <li className={`agent-card agent-card--${agent.key}`} key={agent.key}>
              <span className="agent-mark-wrap">
                <img src={agent.image} alt={agent.key} className="agent-mark-img" />
              </span>
              <div className="agent-copy">
                <span className="agent-maker">{agent.maker}</span>
                <p className="agent-blurb">{agent.blurb}</p>
              </div>
            </li>
          ))}
        </ul>

        <p className="agents-note">More agents are on the way.</p>
      </div>
    </section>
  )
}
