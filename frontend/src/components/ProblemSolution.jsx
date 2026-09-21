import { useEffect, useRef, useState } from 'react'
import {
  motion,
  useMotionValue,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
} from 'framer-motion'

const FRONT_FLOW = ['LONG CHAT', 'HITS TOKEN CAP', 'CONTEXT LOST']
const BACK_FLOW = [
  'FULL CHAT HISTORY',
  '8K-TOKEN EXTRACTION',
  'STRUCTURED MEMORY',
  'NEW AI AGENT',
]

const FRONT_STATS = [
  { value: '128K', label: 'token context window on a modern chat model (2026)' },
  { value: '0%', label: 'of that carries into the next tab you open' },
]
const BACK_STATS = [
  { value: '8K', label: 'tokens is the entire budget each memory run fits into' },
  { value: '~6%', label: 'of a full context window — enough to keep every decision' },
]

function FlowArrow({ className }) {
  return (
    <svg viewBox="0 0 16 24" className={className} aria-hidden="true">
      <path
        d="M8 0v18M2 14l6 7 6-7"
        stroke="currentColor"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// Two real screenshots instead of a drawn mockup: hitting the message limit
// mid-conversation, then a fresh chat with no memory of any of it.
function FrontVisual() {
  return (
    <div className="ps-visual ps-visual--front" aria-hidden="true">
      <div className="ps-shot-stack">
        <div className="ps-shot ps-shot--exhaust">
          <img
            className="ps-shot-img"
            src="/tokenexhaust.png"
            alt="Claude's upgrade dialog after hitting the message limit mid-conversation"
          />
        </div>
        <FlowArrow className="ps-shot-arrow" />
        <div className="ps-shot ps-shot--newchat">
          <img
            className="ps-shot-img"
            src="/newchat.png"
            alt="A new chat replying that it has no access to the previous conversation"
          />
        </div>
      </div>
    </div>
  )
}

function BackVisual() {
  return (
    <div className="ps-visual ps-visual--back" aria-hidden="true">
      <div className="ps-pdf">
        <img
          className="ps-pdf-doc-img"
          src="/memory-export-cover.png"
          alt="First page of an exported memory document: title, source, platform and generated-date fields, instructions for the receiving assistant, and a table of files not included."
        />
      </div>
    </div>
  )
}

function FaceCopy({ side }) {
  const isFront = side === 'front'
  const flow = isFront ? FRONT_FLOW : BACK_FLOW
  const stats = isFront ? FRONT_STATS : BACK_STATS

  return (
    <div className="ps-face-copy">
      <span className={`ps-eyebrow ${isFront ? '' : 'ps-eyebrow--accent'}`}>
        {isFront ? 'THE PROBLEM' : 'THE SOLUTION'}
      </span>
      <h2>
        {isFront
          ? "Problems you've likely faced talking to AI agents."
          : 'Give your next agent a memory.'}
      </h2>
      <p>
        {isFront
          ? "You finally get an agent to understand a concept — then the chat hits a hard token ceiling. The earliest messages get pushed out first: the decisions, the constraints, the explanation that took ten messages to land. Start a new chat and you're teaching it from scratch again."
          : 'We pull what matters out of that chat and rebuild it inside a strict token budget — small enough to run on a free API tier, complete enough for the next agent to pick up exactly where you left off.'}
      </p>

      <div className="ps-stats">
        {stats.map((stat) => (
          <div className="ps-stat" key={stat.label}>
            <span className={`ps-stat-value ${isFront ? '' : 'ps-stat-value--accent'}`}>
              {stat.value}
            </span>
            <span className="ps-stat-label">{stat.label}</span>
          </div>
        ))}
      </div>

      <div className={`ps-flow ${isFront ? 'ps-flow--row' : 'ps-flow--col'}`}>
        {flow.map((label, i) => (
          <div className="ps-flow-step" key={label}>
            <span
              className={`ps-flow-label ${
                i === flow.length - 1 ? 'ps-flow-label--accent' : ''
              }`}
            >
              {label}
            </span>
            {i < flow.length - 1 && (
              <FlowArrow
                className={`ps-flow-arrow ${
                  isFront ? 'ps-flow-arrow--row' : ''
                }`}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function StaticFallback() {
  return (
    <div className="ps-static-stack">
      <div className="ps-static-card">
        <FaceCopy side="front" />
        <FrontVisual />
      </div>
      <div className="ps-static-card">
        <BackVisual />
        <FaceCopy side="back" />
      </div>
    </div>
  )
}

export default function ProblemSolution() {
  const wrapperRef = useRef(null)
  const sceneRef = useRef(null)
  const prefersReducedMotion = useReducedMotion()
  const [tiltEnabled, setTiltEnabled] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(hover: hover) and (pointer: fine)')
    const update = () => setTiltEnabled(mq.matches && !prefersReducedMotion)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [prefersReducedMotion])

  const { scrollYProgress } = useScroll({
    target: wrapperRef,
    offset: ['start start', 'end end'],
  })

  // Hold at the front for the first ~8% and at the back for the last
  // ~12% so the flip itself gets a long, cinematic middle stretch rather
  // than starting the instant the section enters view.
  const rotateYScroll = useTransform(
    scrollYProgress,
    [0, 0.08, 0.88, 1],
    [0, 0, 180, 180],
  )

  const cardShadow = useTransform(
    scrollYProgress,
    [0, 0.44, 0.5, 0.56, 1],
    [
      '0 60px 120px -40px rgba(0,0,0,0.55)',
      '0 26px 54px -26px rgba(0,0,0,0.32)',
      '0 14px 30px -14px rgba(0,0,0,0.22)',
      '0 26px 54px -26px rgba(0,0,0,0.32)',
      '0 60px 120px -40px rgba(0,0,0,0.55)',
    ],
  )

  const tiltXRaw = useMotionValue(0)
  const tiltZRaw = useMotionValue(0)
  const tiltX = useSpring(tiltXRaw, { stiffness: 120, damping: 20, mass: 0.6 })
  const tiltZ = useSpring(tiltZRaw, { stiffness: 120, damping: 20, mass: 0.6 })

  const handlePointerMove = (e) => {
    if (!tiltEnabled || !sceneRef.current) return
    const rect = sceneRef.current.getBoundingClientRect()
    const px = (e.clientX - rect.left) / rect.width - 0.5
    const py = (e.clientY - rect.top) / rect.height - 0.5
    tiltXRaw.set(-py * 9)
    tiltZRaw.set(px * 5)
  }

  const handlePointerLeave = () => {
    tiltXRaw.set(0)
    tiltZRaw.set(0)
  }

  if (prefersReducedMotion) {
    return (
      <section className="ps-section ps-section--static" id="problem-solution">
        <StaticFallback />
      </section>
    )
  }

  return (
    <section className="ps-section" ref={wrapperRef} id="problem-solution">
      <div className="ps-sticky">
        <div
          className="ps-scene"
          ref={sceneRef}
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
        >
          <motion.div
            className="ps-flipcard"
            style={{
              rotateY: rotateYScroll,
              rotateX: tiltX,
              rotateZ: tiltZ,
              boxShadow: cardShadow,
            }}
          >
            <div className="ps-flipcard-edge ps-flipcard-edge--1" aria-hidden="true" />
            <div className="ps-flipcard-edge ps-flipcard-edge--2" aria-hidden="true" />

            <div className="ps-face ps-face--front">
              <div className="ps-face-inner">
                <FaceCopy side="front" />
                <FrontVisual />
              </div>
            </div>

            <div className="ps-face ps-face--back">
              <div className="ps-face-inner ps-face-inner--reverse">
                <BackVisual />
                <FaceCopy side="back" />
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
