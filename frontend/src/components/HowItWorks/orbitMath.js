// Geometry for the "cylinder" carousel.
//
// Four cards are mounted around an invisible VERTICAL cylinder and the
// viewer looks straight at it. One angle (degrees) drives every card's
// position on that cylinder:
//   0   = FRONT  (nearest the viewer — dominant, centred)
//   90  = RIGHT  (on the curved side, partially visible)
//   180 = BACK   (farthest — mostly hidden behind the front card)
//   270 = LEFT   (on the curved side, partially visible)
//
// Movement is horizontal only (x) — the cylinder's axis is vertical, so a
// card never moves up or down, and "depth" (how close a card is to the
// front) is expressed directly as scale + opacity rather than a real
// translateZ. A card here never rotates — it always faces the viewer — and
// for a plane that never turns, real CSS perspective on translateZ produces
// nothing but a uniform size change anyway (no distortion, since the plane
// stays perpendicular to the view axis). Computing that size change
// ourselves gives the identical picture without the actual 3D compositing:
// real perspective + preserve-3d + opacity siblings turned out to be
// genuinely unreliable in Chromium (a card fully covered by a nearer, opaque
// sibling would still paint through it on some frames). Plain x + scale +
// opacity + z-index has none of that ambiguity — it's ordinary 2D stacking.
//
// Step N+1 sits 90 degrees ahead of step N. The shared angle value counts
// DOWN over time, which sends the front card toward the left/back and pulls
// the right card into the front — the anticlockwise sweep the design calls
// for (see Orbit.jsx's rAF loop).

export const STEP_GAP = 90
export const SECONDS_PER_REVOLUTION = 26
export const DEG_PER_SECOND = 360 / SECONDS_PER_REVOLUTION
export const FLOW_SECONDS = 2.8

// Card box is a fixed design size in both modes so the miniature interfaces
// inside never have to be re-laid out — only the cylinder around them changes.
// cardW/cardH are the card's true rendered size at the front (scale 1) —
// there's no perspective magnification stacked on top any more, so this
// number is exactly what appears on screen (before the responsive fit-scale
// in Orbit.jsx, which only ever shrinks to fit a narrow viewport).
export const DESKTOP = {
  rx: 450, // how far the side cards sit from centre, in px
  cardW: 820,
  cardH: 500,
  stageW: 1500,
  stageH: 700,
  arrowRx: 610,
  arrowRy: 180,
  showFlow: true,
  scaleRange: [0.4, 1],
  opacityRange: [0.4, 1],
}

// Phones can't spare the horizontal room a full-width cylinder needs, so the
// radius shrinks — but it stays a real cylinder (cards still move in x,
// never y) rather than collapsing back into a flat stack.
export const COMPACT = {
  rx: 140,
  cardW: 250,
  cardH: 320,
  stageW: 300,
  stageH: 370,
  arrowRx: 150,
  arrowRy: 70,
  showFlow: false,
  scaleRange: [0.55, 1],
  opacityRange: [0.5, 1],
}

const toRad = (deg) => (deg * Math.PI) / 180

export const orbitX = (deg, cfg) => cfg.rx * Math.sin(toRad(deg))

// 1 at the front, -1 at the back.
export const orbitDepth = (deg) => Math.cos(toRad(deg))

// 0 at the back, 1 at the front — the shaping input for scale/opacity/shadow.
export const depthMix = (deg) => (orbitDepth(deg) + 1) / 2

export const lerp = (a, b, t) => a + (b - a) * t

// Direction of travel at a point on the decorative flow ellipse, in degrees,
// for pointing arrowheads. Derivative of (rx*sin, ry*cos) w.r.t. the angle —
// this ellipse is a flat 2D overlay, independent of the cards' own x/z path.
export const tangentDeg = (deg, cfg) => {
  const rad = toRad(deg)
  return (Math.atan2(-cfg.ry * Math.sin(rad), cfg.rx * Math.cos(rad)) * 180) / Math.PI
}
