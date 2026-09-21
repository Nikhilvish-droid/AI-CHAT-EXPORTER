import './Footer.css'

const EXPLORE_LINKS = [
  { label: 'Home', href: '#hero' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'FAQ', href: '#faq-heading' },
]

const PRODUCT_LINKS = [
  { label: 'Submit Chat', href: '#hero' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'FAQ', href: '#faq-heading' },
]

function FlowMark() {
  return (
    <svg className="footer-mark" width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="4" cy="12" r="2.3" fill="currentColor" opacity="0.55" />
      <circle cx="12" cy="12" r="2.3" fill="currentColor" />
      <circle cx="20" cy="12" r="2.3" fill="currentColor" opacity="0.85" />
      <path d="M6.6 12H9.4M14.6 12H17.4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-decor" aria-hidden="true">
        <span className="footer-glow" />
        <span className="footer-dot footer-dot--a" />
        <span className="footer-dot footer-dot--b" />
        <span className="footer-dot footer-dot--c" />
      </div>

      <div className="footer-inner">
        <div className="footer-top">
          <div className="footer-brand">
            <a href="#hero" className="footer-logo">
              <FlowMark />
              <span>AI CHAT EXPORTER</span>
            </a>
            <p className="footer-tagline-brand">
              Turn old AI conversations into reusable memory.
            </p>
            <p className="footer-desc">
              Export the context, decisions and technical knowledge from your
              previous AI conversations and carry them into your next AI agent.
            </p>
          </div>

          <nav className="footer-col" aria-labelledby="footer-explore-heading">
            <p id="footer-explore-heading" className="footer-col-heading">
              Explore
            </p>
            <ul className="footer-links">
              {EXPLORE_LINKS.map((link) => (
                <li key={link.label}>
                  <a href={link.href}>{link.label}</a>
                </li>
              ))}
            </ul>
          </nav>

          <nav className="footer-col" aria-labelledby="footer-product-heading">
            <p id="footer-product-heading" className="footer-col-heading">
              Memory Exporter
            </p>
            <ul className="footer-links">
              {PRODUCT_LINKS.map((link) => (
                <li key={link.label}>
                  <a href={link.href}>{link.label}</a>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        <div className="footer-divider" />

        <div className="footer-bottom">
          <p className="footer-copyright">© 2026 AI Chat Exporter. All rights reserved.</p>
          <p className="footer-signoff">Built for better AI handoffs.</p>
          <p className="footer-credit">
            Made by Nikhil <span className="footer-heart">❤️</span>
          </p>
        </div>
      </div>
    </footer>
  )
}
