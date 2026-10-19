import { useEffect, useState } from 'react'
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
  const [solid, setSolid] = useState(false)

  // Solid once the first section after the hero reaches the nav.
  useEffect(() => {
    const update = () => {
      const after = document.getElementById('problem-solution')
      setSolid(!!after && after.getBoundingClientRect().top <= 64)
    }
    update()
    window.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)
    return () => {
      window.removeEventListener('scroll', update)
      window.removeEventListener('resize', update)
    }
  }, [])

  return (
    <header className={`site-nav${solid ? ' is-solid' : ''}`}>
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
