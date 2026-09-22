import { useLayoutEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import SubmitBox from './SubmitBox'

gsap.registerPlugin(ScrollTrigger)
// Prevents GSAP from re-measuring (and jumping) the pin every time a mobile
// browser's address bar shows/hides mid-scroll — without this, pinned
// scroll effects are unreliable on phones.
ScrollTrigger.config({ ignoreMobileResize: true })

// Small puffs that drift near the rim once the cave is in frame.
const AMBIENT_CLOUDS = [
  { src: '/clouds02.webp', top: '20%', left: '4%', width: '22%', opacity: 0.5, drift: 14 },
  { src: '/clouds05.webp', top: '12%', left: '70%', width: '26%', opacity: 0.45, drift: 18 },
  { src: '/clouds09.webp', top: '60%', left: '74%', width: '22%', opacity: 0.4, drift: 16 },
]

// The bank of cloud the page opens inside — dense enough at rest that the
// mountain barely shows through, then parts outward (slowly) as you scroll.
// `depth` scales how far each layer drifts with the cursor (closer/bigger
// clouds move more, giving the bank a sense of layered thickness).
const FOG_CLOUDS = [
  // back layer: large, soft, fills the gaps between the foreground puffs
  { src: '/clouds03.webp', top: '-30%', left: '-35%', width: '120%', dx: -30, dy: -18, depth: 0.4 },
  { src: '/clouds03.webp', top: '20%', left: '10%', width: '130%', dx: 10, dy: 22, depth: 0.4 },
  { src: '/clouds01.webp', top: '45%', left: '-25%', width: '110%', dx: -34, dy: 20, depth: 0.5 },
  { src: '/clouds01.webp', top: '-25%', left: '30%', width: '105%', dx: 14, dy: -30, depth: 0.5 },
  // foreground layer: denser, more contrast, the ones that visibly "part"
  { src: '/clouds07.webp', top: '-16%', left: '-15%', width: '88%', dx: -38, dy: -20, depth: 0.9 },
  { src: '/clouds11.webp', top: '-10%', left: '35%', width: '82%', dx: 6, dy: -34, depth: 0.9 },
  { src: '/clouds09.webp', top: '-14%', left: '62%', width: '85%', dx: 40, dy: -22, depth: 0.9 },
  { src: '/clouds11.webp', top: '30%', left: '-20%', width: '86%', dx: -42, dy: 4, depth: 1 },
  { src: '/clouds05.webp', top: '32%', left: '38%', width: '70%', dx: 2, dy: 6, depth: 1 },
  { src: '/clouds09.webp', top: '28%', left: '68%', width: '80%', dx: 42, dy: 2, depth: 1 },
  { src: '/clouds07.webp', top: '58%', left: '-18%', width: '85%', dx: -38, dy: 28, depth: 0.9 },
  { src: '/clouds05.webp', top: '62%', left: '20%', width: '78%', dx: 4, dy: 36, depth: 0.9 },
  { src: '/clouds11.webp', top: '56%', left: '55%', width: '84%', dx: 38, dy: 26, depth: 0.9 },
]

// top/left/width percentages above are sized against a wide/short desktop
// frame, where container height is small relative to width. On a narrow/tall
// phone frame the same percentages leave the bank far too short — it only
// bridges a band in the middle, exposing the mountain above it and a flat,
// textureless strip of the fog backing below it. This variant uses much
// larger widths (so each cloud's auto height, tied to its own image aspect
// ratio, actually spans a meaningful share of a tall viewport) and a top
// spread that runs from above the frame to well past its bottom edge.
const FOG_CLOUDS_MOBILE = [
  { src: '/clouds03.webp', top: '-22%', left: '-55%', width: '230%', dx: -20, dy: -14, depth: 0.4 },
  { src: '/clouds01.webp', top: '4%', left: '-40%', width: '210%', dx: 24, dy: -10, depth: 0.5 },
  { src: '/clouds07.webp', top: '-6%', left: '-20%', width: '190%', dx: -26, dy: -16, depth: 0.9 },
  { src: '/clouds11.webp', top: '16%', left: '-45%', width: '215%', dx: 22, dy: 12, depth: 0.9 },
  { src: '/clouds09.webp', top: '30%', left: '-15%', width: '195%', dx: -22, dy: 14, depth: 1 },
  { src: '/clouds05.webp', top: '42%', left: '-35%', width: '200%', dx: 18, dy: -10, depth: 1 },
  { src: '/clouds01.webp', top: '56%', left: '-20%', width: '190%', dx: -24, dy: 16, depth: 0.5 },
  { src: '/clouds07.webp', top: '68%', left: '-45%', width: '215%', dx: 26, dy: 10, depth: 0.9 },
  { src: '/clouds11.webp', top: '80%', left: '-15%', width: '195%', dx: -20, dy: -12, depth: 0.9 },
  { src: '/clouds09.webp', top: '92%', left: '-40%', width: '210%', dx: 22, dy: 8, depth: 1 },
]

export default function CaveHero() {
  const wrapRef = useRef(null)
  const skyRef = useRef(null)
  const mountainRef = useRef(null)
  const explorerRef = useRef(null)
  const caveRef = useRef(null)
  const scrollCueRef = useRef(null)
  const submitBoxRef = useRef(null)
  const fogRef = useRef(null)
  const fogCloudRefs = useRef([])
  const headlineRef = useRef(null)
  const ambientRefs = useRef([])
  // Same narrow/wide split the layout effect below uses, computed once up
  // front (lazy initializer — safe since this is client-only) so the JSX
  // below and the animation logic stay in sync about which cloud layout is
  // actually on screen.
  const [fogClouds] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(max-aspect-ratio: 1/1)').matches
      ? FOG_CLOUDS_MOBILE
      : FOG_CLOUDS,
  )

  useLayoutEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    // Declared here (not inside the gsap.context callback below) so the
    // cleanup closure can actually reach it.
    let onPointerMove = null

    // Mountains.png / Bg_Sky.png are portrait photos whose lower two-thirds
    // is genuinely dark foreground/treeline. On landscape screens `cover`
    // crops most of that away (top/bottom crop). On narrow/tall screens
    // `cover` flips to cropping the sides instead, so the *full* height
    // shows — including much more of that dark lower portion, which reads
    // as a big empty gap between the terrain and the figure. Zooming in a
    // bit further on narrow screens pushes more of the bright terrain into
    // frame and less of the dark foreground, closing that gap.
    const narrow = window.matchMedia('(max-aspect-ratio: 1/1)').matches
    const settledScale = narrow ? 1.35 : 1
    // On the resting (pre-scroll) frame, narrow screens need a heavier crop
    // than the settled/revealed frame does: zoomed in enough to push the
    // dark treeline out of view, then panned down (yPercent) so the peak
    // lands mid-frame instead of hugging the very top edge under the nav.
    // The pan alone would leave a gap above the mountain once the fog bank
    // clears (nothing there but the hero's own near-black background) —
    // Mountains.png has ~9% of transparent margin above the peak, and
    // panning down by more than the scale can "cover" pushes that margin's
    // new position past the top edge. Sky sits directly behind it and is
    // fully opaque, so scaling *it* up enough to always reach the top edge
    // (0.5*(scale-1) ≥ pan) fills that gap with actual sky colour instead
    // of flat black; the mountain gets a smaller bump too, mostly to keep
    // less of its own dark foreground exposed at the bottom.
    const restMountainScale = narrow ? 1.5 : 1.32
    const restSkyScale = narrow ? 1.9 : 1.18
    const restYPercent = narrow ? 40 : 0

    // `yPercent` scales to each element's OWN height, so the full-height
    // explorer image and the much shorter submit box would travel very
    // different pixel distances for the same "100%" — the box would
    // visibly arrive long before he does. Using the same measured pixel
    // distance for both is what actually makes them rise together.
    const riseDistance = wrapRef.current.getBoundingClientRect().height

    const ctx = gsap.context(() => {
      // Resting state before any scroll: clouded in, zoomed-in mountain,
      // no cave, no figure, no cue.
      gsap.set(caveRef.current, { scale: 3.2 })
      gsap.set(mountainRef.current, { scale: restMountainScale, yPercent: restYPercent })
      gsap.set(skyRef.current, { scale: restSkyScale, yPercent: restYPercent })
      // Off-screen below the frame (not just invisible) — the figure and
      // the box he holds rise into place together, as one unit, rather
      // than him appearing first and the box fading in separately later.
      // Both use the same pixel distance (see riseDistance above) so they
      // move at the same visual rate.
      gsap.set(explorerRef.current, { y: riseDistance })
      gsap.set(submitBoxRef.current, { y: riseDistance, opacity: 1 })
      gsap.set(headlineRef.current, { opacity: 0, y: 30 })
      gsap.set(scrollCueRef.current, { opacity: 0 })
      gsap.set(ambientRefs.current.filter(Boolean), { opacity: 0 })

      if (reduced) {
        gsap.set(caveRef.current, { scale: 1 })
        gsap.set(mountainRef.current, { scale: 1 })
        gsap.set(skyRef.current, { scale: 1 })
        gsap.set(explorerRef.current, { y: 0 })
        gsap.set(submitBoxRef.current, { y: 0 })
        gsap.set(fogRef.current, { opacity: 0 })
        gsap.set(scrollCueRef.current, { opacity: 0 })
        return
      }

      // Idle drift on the rim puffs — independent of scroll.
      ambientRefs.current.forEach((el, i) => {
        if (!el) return
        gsap.to(el, {
          x: (i % 2 === 0 ? 1 : -1) * AMBIENT_CLOUDS[i].drift,
          y: (i % 2 === 0 ? -1 : 1) * (AMBIENT_CLOUDS[i].drift * 0.5),
          duration: 6 + i,
          ease: 'sine.inOut',
          repeat: -1,
          yoyo: true,
        })
      })

      // Slow churn on the fog bank itself so it looks alive before you scroll.
      fogCloudRefs.current.forEach((el, i) => {
        if (!el) return
        gsap.to(el, {
          xPercent: (i % 2 === 0 ? 1 : -1) * 3,
          yPercent: (i % 3 === 0 ? -1 : 1) * 2,
          duration: 9 + (i % 4) * 2,
          ease: 'sine.inOut',
          repeat: -1,
          yoyo: true,
        })
      })

      // Cursor parallax on the fog bank — each layer drifts a little with
      // the pointer (scaled by its `depth`), so the cloud reads as a stack
      // of layers rather than a flat image, even before any scrolling.
      const cloudMovers = fogCloudRefs.current.map((el) =>
        el
          ? {
              // Slower, more languid follow (was 1.1s) — a quick snap read
              // as jittery/fast rather than a natural drift.
              x: gsap.quickTo(el, 'x', { duration: 2, ease: 'power2.out' }),
              y: gsap.quickTo(el, 'y', { duration: 2, ease: 'power2.out' }),
            }
          : null,
      )
      onPointerMove = (e) => {
        const nx = (e.clientX / window.innerWidth - 0.5) * 2
        const ny = (e.clientY / window.innerHeight - 0.5) * 2
        cloudMovers.forEach((mover, i) => {
          if (!mover) return
          const depth = fogClouds[i].depth * 20
          mover.x(nx * depth)
          mover.y(ny * depth * 0.6)
        })
      }
      window.addEventListener('pointermove', onPointerMove, { passive: true })

      const tl = gsap.timeline({
        scrollTrigger: {
          id: 'cave-reveal',
          trigger: wrapRef.current,
          start: 'top top',
          end: '+=650%',
          // Smooths out inconsistent wheel/trackpad deltas without making
          // the animation visibly trail behind the scrollbar.
          scrub: 1.5,
          pin: true,
          anticipatePin: 1,
        },
      })

      // ---- Phase A: the cloud bank parts (slowly) and the headline arrives ----
      // Given a smaller share of the timeline than before (was ~50%, now
      // ~32%) so phase B — which has more staged reveals — isn't left
      // cramming six events into the same amount of scroll distance that
      // phase A used for two.
      fogCloudRefs.current.forEach((el, i) => {
        if (!el) return
        const c = fogClouds[i]
        tl.to(
          el,
          { xPercent: c.dx, yPercent: c.dy, scale: 1.3, ease: 'none', duration: 0.32 },
          0,
        )
      })
      tl.to(fogRef.current, { opacity: 0, ease: 'none', duration: 0.3 }, 0.06)
      tl.to(headlineRef.current, { opacity: 1, y: 0, ease: 'none', duration: 0.13 }, 0.13)

      // ---- Phase B: pull back and discover the cave ----
      // Each stage now gets noticeably more scroll distance to play out
      // over, so the reveal reads as a steady, natural progression rather
      // than everything happening in a rush right after the headline.
      tl.to(headlineRef.current, { opacity: 0, y: -20, ease: 'none', duration: 0.1 }, 0.32)
      tl.to(caveRef.current, { scale: settledScale, ease: 'none', duration: 0.56 }, 0.32)
      tl.to(
        mountainRef.current,
        { scale: settledScale, yPercent: 0, ease: 'none', duration: 0.56 },
        0.32,
      )
      tl.to(skyRef.current, { scale: settledScale, yPercent: 0, ease: 'none', duration: 0.56 }, 0.32)
      // Figure and box rise together as one unit — same start point, same
      // duration — instead of him arriving first and the box fading in on
      // its own later.
      tl.to(explorerRef.current, { y: 0, ease: 'none', duration: 0.26 }, 0.55)
      tl.to(submitBoxRef.current, { y: 0, ease: 'none', duration: 0.26 }, 0.55)
      tl.to(
        ambientRefs.current.filter(Boolean),
        { opacity: (i) => AMBIENT_CLOUDS[i].opacity, ease: 'none', duration: 0.22 },
        0.68,
      )
      // Scroll cue's job is done once the figure (and what he's carrying)
      // has arrived.
      tl.to(scrollCueRef.current, { opacity: 1, ease: 'none', duration: 0.08 }, 0.86)
      tl.to(scrollCueRef.current, { opacity: 0, ease: 'none', duration: 0.06 }, 0.94)
    }, wrapRef)

    return () => {
      if (onPointerMove) window.removeEventListener('pointermove', onPointerMove)
      ctx.revert()
    }
  }, [])

  return (
    <section className="cave-hero-wrap" ref={wrapRef} id="hero">
      <div className="cave-hero-pin">
        <img className="cave-layer cave-layer--sky" ref={skyRef} src="/Bg_Sky.webp" alt="" />
        <img
          className="cave-layer cave-layer--mountain"
          ref={mountainRef}
          src="/Mountains.webp"
          alt=""
        />
        <img
          className="cave-layer cave-layer--explorer"
          ref={explorerRef}
          src="/Explorer-boy.webp"
          alt=""
        />

        {AMBIENT_CLOUDS.map((c, i) => (
          <img
            key={`${c.src}-${i}`}
            ref={(el) => (ambientRefs.current[i] = el)}
            className="cave-cloud cave-cloud--ambient"
            src={c.src}
            alt=""
            style={{ top: c.top, left: c.left, width: c.width }}
          />
        ))}

        <img className="cave-layer cave-layer--cave" ref={caveRef} src="/Cave.webp" alt="" />

        <div className="reveal-headline" ref={headlineRef}>
          <h1>
            <span className="lead">Agent memory transfer</span>
            <span className="main">
              Is your agent&rsquo;s
              <br />
              token limit exhausted?
            </span>
            <span className="rule" />
          </h1>
        </div>

        <div className="scroll-cue" ref={scrollCueRef}>
          <img src="/Mouse-alt.png" alt="" />
          <span>Scroll</span>
        </div>

        <div className="submit-box-wrap" ref={submitBoxRef}>
          <SubmitBox />
        </div>

        <div className="fog-curtain" ref={fogRef}>
          {fogClouds.map((c, i) => (
            <img
              key={`${c.src}-${i}`}
              ref={(el) => (fogCloudRefs.current[i] = el)}
              src={c.src}
              alt=""
              style={{ top: c.top, left: c.left, width: c.width }}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
