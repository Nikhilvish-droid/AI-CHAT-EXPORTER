import { useEffect, useState } from 'react'
import { useReducedMotion } from 'framer-motion'
import Orbit from './Orbit'
import { StepFace } from './StepCard'
import { COMPACT, DESKTOP } from './orbitMath'
import { STEPS } from './steps'

function useMedia(query) {
  const [matches, setMatches] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const update = () => setMatches(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [query])
  return matches
}

function SectionHead() {
  return (
    <header className="hiw-head">
      <span className="hiw-eyebrow">THE PROCESS</span>
      <h2>From conversation to continuity.</h2>
      <p>
        Turn your previous AI conversation into structured memory that your next agent can
        understand.
      </p>
    </header>
  )
}

function StaticSteps() {
  return (
    <ol className="hiw-static-grid">
      {STEPS.map((step, i) => (
        <li className="hiw-static-card" key={step.num}>
          <StepFace step={step} index={i} />
          <span className="hiw-static-arrow" aria-hidden="true">
            <svg viewBox="0 0 24 12">
              <path
                d="M1 6h17M14 1.5 19.5 6 14 10.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        </li>
      ))}
    </ol>
  )
}

export default function HowItWorks() {
  const prefersReducedMotion = useReducedMotion()
  const compact = useMedia('(max-width: 900px)')
  const finePointer = useMedia('(hover: hover) and (pointer: fine)')

  if (prefersReducedMotion) {
    return (
      <section className="hiw-section hiw-section--static" id="how-it-works" aria-label="How it works">
        <SectionHead />
        <StaticSteps />
      </section>
    )
  }

  const cfg = compact ? COMPACT : DESKTOP

  return (
    <section className="hiw-section" id="how-it-works" aria-label="How it works">
      <SectionHead />
      {/* Remounting on breakpoint change rebinds every orbit transform to the
          new geometry in one go. */}
      <Orbit
        key={compact ? 'compact' : 'wide'}
        cfg={cfg}
        compact={compact}
        parallax={finePointer && !compact}
      />
      {compact && (
        <ol className="hiw-legend" aria-hidden="true">
          {STEPS.map((step) => (
            <li key={step.num}>
              <span>{step.num}</span>
              {step.title}
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
