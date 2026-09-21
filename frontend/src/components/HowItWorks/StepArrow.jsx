import { motion, useTransform } from 'framer-motion'
import { STEP_GAP, depthMix, lerp, tangentDeg } from './orbitMath'

// The orbit line is a flat 2D ellipse drawn just outside the cards' own path —
// the cylinder's circular footprint, as if viewed from slightly above. Same
// centre, same angles, same direction as the cards' x/z motion — just wide
// enough to clear them.
const track = (cfg) => ({ rx: cfg.arrowRx, ry: cfg.arrowRy })

const trackX = (deg, cfg) => track(cfg).rx * Math.sin((deg * Math.PI) / 180)
const trackY = (deg, cfg) => track(cfg).ry * Math.cos((deg * Math.PI) / 180)

function Arrowhead({ index, angle, cfg }) {
  const at = (v) => v + index * STEP_GAP + STEP_GAP / 2

  const x = useTransform(angle, (v) => trackX(at(v), cfg))
  const y = useTransform(angle, (v) => trackY(at(v), cfg))
  const rotate = useTransform(angle, (v) => tangentDeg(at(v), track(cfg)))
  const opacity = useTransform(angle, (v) => lerp(0.3, 0.95, depthMix(at(v))))
  const scale = useTransform(angle, (v) => lerp(0.7, 1, depthMix(at(v))))

  return (
    <motion.div className="hiw-arrow" style={{ x, y, rotate, opacity, scale }}>
      <svg viewBox="0 0 40 14" aria-hidden="true">
        <path
          d="M1 7h26"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinecap="round"
          opacity="0.5"
        />
        <path
          d="M26 1.5 33.5 7 26 12.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </motion.div>
  )
}

function Packet({ index, angle, flow, cfg }) {
  // Rides from its own card to the next one, then restarts — the reset is
  // hidden by fading the packet out at both ends of the run.
  const at = (v, p) => v + index * STEP_GAP + STEP_GAP * p

  const x = useTransform([angle, flow], ([v, p]) => trackX(at(v, p), cfg))
  const y = useTransform([angle, flow], ([v, p]) => trackY(at(v, p), cfg))
  const opacity = useTransform([angle, flow], ([v, p]) => {
    const fade = Math.sin(Math.PI * p)
    return fade * lerp(0.25, 1, depthMix(at(v, p)))
  })
  const scale = useTransform([angle, flow], ([v, p]) => lerp(0.6, 1, depthMix(at(v, p))))

  return <motion.span className="hiw-packet" style={{ x, y, opacity, scale }} />
}

export default function StepArrow({ angle, flow, cfg }) {
  return (
    <div className="hiw-flow" aria-hidden="true">
      {[0, 1, 2, 3].map((i) => (
        <Arrowhead key={`a${i}`} index={i} angle={angle} cfg={cfg} />
      ))}
      {[0, 1, 2, 3].map((i) => (
        <Packet key={`p${i}`} index={i} angle={angle} flow={flow} cfg={cfg} />
      ))}
    </div>
  )
}
