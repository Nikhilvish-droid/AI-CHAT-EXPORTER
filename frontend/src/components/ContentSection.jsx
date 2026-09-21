import { useLayoutEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const GALLERY = [
  { src: '/gallery/gallery-1.jpg', alt: 'Snow-capped peak at dusk' },
  { src: '/gallery/gallery-3.jpg', alt: 'Two hikers walking toward the mountains' },
  { src: '/gallery/gallery-2.jpg', alt: 'Cloud-wrapped mountain range' },
]

export default function ContentSection() {
  const sectionRef = useRef(null)
  const cardRefs = useRef([])

  useLayoutEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduced) return undefined

    const ctx = gsap.context(() => {
      gsap.fromTo(
        cardRefs.current,
        { opacity: 0, y: 60 },
        {
          opacity: 1,
          y: 0,
          duration: 0.9,
          ease: 'power3.out',
          stagger: 0.12,
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top 70%',
          },
        },
      )
    }, sectionRef)

    return () => ctx.revert()
  }, [])

  return (
    <section className="content-section" ref={sectionRef} id="services">
      <h2>Beautiful parallax designed to inspire your creativity.</h2>
      <p className="content-copy">
        Etiam id facilisis erat, posuere bibendum nulla. Praesent nec dui dui.
        Donec suscipit sed ligula ac cursus. Sed quis gravida elit.
      </p>

      <div className="gallery-row">
        {GALLERY.map((img, i) => (
          <div
            className="gallery-card"
            key={img.src}
            ref={(el) => (cardRefs.current[i] = el)}
          >
            <img src={img.src} alt={img.alt} loading="lazy" />
          </div>
        ))}
      </div>
    </section>
  )
}
