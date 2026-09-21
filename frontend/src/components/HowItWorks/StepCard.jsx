import { motion, useTransform } from 'framer-motion'
import { STEP_GAP, depthMix, lerp, orbitX } from './orbitMath'
import { TOTAL } from './steps'

// The card body is identical in the orbit and in the reduced-motion fallback,
// so the two can never drift apart in content.
export function StepFace({ step, index }) {
  const { Visual } = step
  return (
    <div className="hiw-card-face">
      <div className="hiw-card-edge hiw-card-edge--1" aria-hidden="true" />
      <div className="hiw-card-edge hiw-card-edge--2" aria-hidden="true" />

      <div className="hiw-card-body">
        <header className="hiw-card-head">
          <span className="hiw-step-no">
            {step.num}
            <i> / {TOTAL}</i>
          </span>
          <span className="hiw-step-pips" aria-hidden="true">
            {Array.from({ length: 4 }, (_, i) => (
              <i key={i} className={i === index ? 'is-on' : undefined} />
            ))}
          </span>
        </header>

        <h3 className="hiw-card-title">{step.title}</h3>
        <p className="hiw-card-desc">{step.desc}</p>

        <div className="hiw-card-visual">
          <div className="hiw-visual-fit">
            <Visual />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function StepCard({ step, index, angle, cfg, onHover, cardRef }) {
  const at = (v) => v + index * STEP_GAP

  // Plain 2D transforms only — no translateZ, no CSS perspective. For a card
  // that never rotates (always facing the viewer, billboard-style), real 3D
  // perspective on translateZ produces nothing but a uniform size change —
  // exactly what `scale` already gives us directly, with none of the
  // compositing ambiguity real 3D + opacity siblings turned out to have.
  //
  // No z-index here either — stacking order comes from real DOM order,
  // managed by Orbit.jsx. Animating z-index every frame forces the main
  // thread to recompute stacking on its own schedule, separate from the
  // compositor-only transform/opacity animation running everything else —
  // the two falling one frame out of sync is what let a fully-covered card
  // visibly paint through an opaque one in front of it.
  const x = useTransform(angle, (v) => orbitX(at(v), cfg))
  const scale = useTransform(angle, (v) => lerp(...cfg.scaleRange, depthMix(at(v))))
  // Opacity ramps all the way to true zero as a card nears the back, rather
  // than levelling off at a visible floor — a card that's fully transparent
  // there has nothing to show even if something briefly gets its paint order
  // wrong, and a card that's actually behind the front one is exactly what
  // "mostly hidden" means anyway. Cards stay clearly visible through the
  // whole side arc (90°/270°) — only the narrow final stretch into the back
  // position fades away.
  const opacity = useTransform(angle, (v) => {
    const t = (depthMix(at(v)) - 0.15) / 0.85
    return lerp(0, cfg.opacityRange[1], Math.max(0, Math.min(1, t)))
  })
  const boxShadow = useTransform(angle, (v) => {
    const t = depthMix(at(v))
    return `0 ${lerp(14, 60, t)}px ${lerp(30, 100, t)}px -${lerp(14, 30, t)}px rgba(4, 2, 12, ${lerp(
      0.28,
      0.6,
      t,
    )})`
  })

  return (
    <motion.li
      ref={cardRef}
      className="hiw-card"
      style={{ x, scale, opacity, boxShadow }}
      onPointerEnter={() => onHover(true)}
      onPointerLeave={() => onHover(false)}
    >
      <StepFace step={step} index={index} />
    </motion.li>
  )
}
