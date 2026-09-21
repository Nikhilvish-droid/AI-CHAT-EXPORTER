export default function Nav() {
  return (
    <header className="site-nav">
      <div className="site-nav-bar" />
      <a href="#hero" className="site-logo">
        <img src="/projectlogo/icon-transparent.png" alt="AI Chat Exporter" />
        <span>AI Chat Exporter</span>
      </a>
      <nav>
        <a href="#hero" className="active">Home</a>
      </nav>
    </header>
  )
}
