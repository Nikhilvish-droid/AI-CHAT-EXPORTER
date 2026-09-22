import { ScrollTrigger } from 'gsap/ScrollTrigger'

// The submit box lives inside CaveHero's pinned scroll-reveal (see
// CaveHero.jsx) rather than at its own place in the page, so "navigating" to
// it means scrolling partway through that pin — to just past the point where
// the box has fully risen into view (progress 0.55–0.81 in the timeline).
function goToSubmitBox(e) {
  e.preventDefault()
  const trigger = ScrollTrigger.getById('cave-reveal')
  if (!trigger) {
    document.getElementById('hero')?.scrollIntoView({ behavior: 'smooth' })
    return
  }
  const target = trigger.start + (trigger.end - trigger.start) * 0.85
  window.scrollTo({ top: target, behavior: 'smooth' })
}

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
        <a href="#hero" className="active" onClick={goToSubmitBox}>Submit</a>
      </nav>
    </header>
  )
}
