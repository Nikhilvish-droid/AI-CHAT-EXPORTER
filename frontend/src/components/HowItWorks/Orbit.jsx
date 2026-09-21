import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import StepArrow from './StepArrow'
import StepCard from './StepCard'
import { DEG_PER_SECOND, FLOW_SECONDS, STEP_GAP, orbitDepth } from './orbitMath'
import { STEPS } from './steps'

const INITIAL_ORDER = [0, 1, 2, 3]

// Back-to-front order of the four cards at the current angle: index 0 is
// farthest away, index 3 is the front card. Used to control paint order
// through real DOM order instead of an animated z-index.
function depthOrder(angleDeg) {
  return INITIAL_ORDER.slice().sort(
    (a, b) => orbitDepth(angleDeg + a * STEP_GAP) - orbitDepth(angleDeg + b * STEP_GAP),
  )
}

// Hovering a card eases the ring down rather than stopping it dead, so the
// carousel keeps its rhythm while you read.
const HOVER_SPEED = 0.12

export default function Orbit({ cfg, parallax, compact }) {
  const wrapRef = useRef(null)
  const ringRef = useRef(null)
  const cardRefs = useRef([null, null, null, null])
  const angle = useMotionValue(0)
  const flow = useMotionValue(0)
  const speedRef = useRef(1)
  const [running, setRunning] = useState(false)
  const [scale, setScale] = useState(1)
  const orderRef = useRef(INITIAL_ORDER)

  // Only a boolean ever reaches React state — the angle itself lives in a
  // motion value and never triggers a render.
  useEffect(() => {
    const el = wrapRef.current
    if (!el) return

    let onscreen = false
    const sync = () => setRunning(onscreen && !document.hidden)
    const io = new IntersectionObserver(
      ([entry]) => {
        onscreen = entry.isIntersecting
        sync()
      },
      { rootMargin: '140px' },
    )

    io.observe(el)
    document.addEventListener('visibilitychange', sync)
    return () => {
      io.disconnect()
      document.removeEventListener('visibilitychange', sync)
    }
  }, [])

  // Reordered imperatively, direct DOM manipulation, deliberately outside
  // React state — Framer Motion's x/scale/opacity above are applied straight
  // to the DOM every frame, completely bypassing React's render cycle
  // (that's what makes them cheap enough to run at 60fps). A React state
  // update instead is scheduled and batched on its own timeline, so a
  // reorder driven by setState could commit a frame or more after the
  // opacity from this same tick had already changed — and for that gap, a
  // card reading as "more in front" by opacity was still behind in actual
  // paint order. That gap is exactly what let a fully-covered card visibly
  // paint through an opaque one in front of it. appendChild on an
  // already-attached node just moves it (no remount, no lost state), and
  // calling it here keeps it perfectly synchronous with the same tick's
  // opacity change.
  const syncOrder = useCallback((angleDeg) => {
    const nextOrder = depthOrder(angleDeg)
    if (nextOrder.every((v, i) => v === orderRef.current[i])) return
    orderRef.current = nextOrder
    const list = ringRef.current
    if (!list) return
    for (const i of nextOrder) {
      const el = cardRefs.current[i]
      if (el) list.appendChild(el)
    }
  }, [])

  useEffect(() => {
    syncOrder(angle.get())
  }, [angle, syncOrder])

  useEffect(() => {
    if (!running) return
    let raf = 0
    let last = performance.now()

    const tick = (now) => {
      // Clamped so a backgrounded tab or a long frame can't jump the ring.
      const dt = Math.min(now - last, 80) / 1000
      last = now
      const speed = speedRef.current
      // Counting the angle DOWN sends the front card (angle 0) toward
      // negative angles — i.e. toward the left — while pulling the right
      // card (angle 90) down toward 0: the anticlockwise sweep the design
      // calls for. See orbitMath.js for the full angle convention.
      const nextAngle = angle.get() - dt * DEG_PER_SECOND * speed
      angle.set(nextAngle)
      flow.set((flow.get() + (dt / FLOW_SECONDS) * speed) % 1)
      syncOrder(nextAngle)

      raf = requestAnimationFrame(tick)
    }

    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [running, angle, flow, syncOrder])

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setScale(Math.min(width / cfg.stageW, height / cfg.stageH, 1))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [cfg.stageW, cfg.stageH])

  const handleHover = useCallback((hovering) => {
    speedRef.current = hovering ? HOVER_SPEED : 1
  }, [])

  const pointerX = useMotionValue(0)
  const pointerY = useMotionValue(0)
  const spring = { stiffness: 80, damping: 20, mass: 0.7 }
  const smoothX = useSpring(pointerX, spring)
  const smoothY = useSpring(pointerY, spring)
  const sceneRotateY = useTransform(smoothX, (v) => v * 9)
  const sceneRotateX = useTransform(smoothY, (v) => v * -6)

  const handlePointerMove = (e) => {
    if (!parallax || !wrapRef.current) return
    const rect = wrapRef.current.getBoundingClientRect()
    pointerX.set((e.clientX - rect.left) / rect.width - 0.5)
    pointerY.set((e.clientY - rect.top) / rect.height - 0.5)
  }

  const resetPointer = () => {
    pointerX.set(0)
    pointerY.set(0)
  }

  return (
    <div
      className="hiw-stage-wrap"
      ref={wrapRef}
      onPointerMove={handlePointerMove}
      onPointerLeave={resetPointer}
    >
      <motion.div
        className={`hiw-stage${compact ? ' hiw-stage--compact' : ''}`}
        style={{
          '--card-w': cfg.cardW,
          '--card-h': cfg.cardH,
          width: cfg.stageW,
          height: cfg.stageH,
          scale,
          rotateX: parallax ? sceneRotateX : 0,
          rotateY: parallax ? sceneRotateY : 0,
        }}
      >
        {cfg.showFlow && <StepArrow angle={angle} flow={flow} cfg={cfg} />}

        {/* Rendered in a fixed, arbitrary DOM order — actual paint order is
            corrected imperatively by syncOrder above as soon as it mounts,
            and kept correct every frame after. */}
        <ol className="hiw-ring-list" ref={ringRef}>
          {STEPS.map((step, i) => (
            <StepCard
              key={step.num}
              step={step}
              index={i}
              angle={angle}
              cfg={cfg}
              onHover={handleHover}
              cardRef={(el) => {
                cardRefs.current[i] = el
              }}
            />
          ))}
        </ol>
      </motion.div>
    </div>
  )
}
