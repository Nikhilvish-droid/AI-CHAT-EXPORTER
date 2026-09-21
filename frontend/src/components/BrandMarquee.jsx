// How many items make up one loop unit. Wide enough that a single group's
// rendered width comfortably exceeds any realistic viewport — the
// seamless-loop trick (two identical groups, animate translateX(-50%) ->
// translateX(0%)) only reads as gapless if you can never scroll far enough
// to see where a group actually ends.
const REPEAT_COUNT = 10

// The two phrases alternate item-by-item rather than one being a rare
// insert — every other slot is the secondary line.
const CONTENT = ['AI Chat Exporter', 'Context → Memory → New Agent']

// A single bold diagonal cut — two parallel slanted edges with the sliver
// between them filled solid black.
function CutSeparator() {
  return (
    <svg className="marquee-sep" viewBox="0 0 15 24" aria-hidden="true">
      <path d="M9 1 L15 1 L6 23 L0 23 Z" />
    </svg>
  )
}

// Text and separators are direct flex children of .marquee-group so the
// group's own `gap` sets the breathing room between every repeated phrase
// uniformly, instead of a nested per-item wrapper.
function MarqueeGroup() {
  return (
    <div className="marquee-group">
      {Array.from({ length: REPEAT_COUNT }).flatMap((_, i) => [
        <span key={`t-${i}`} className={i % 2 === 1 ? 'marquee-text marquee-text--alt' : 'marquee-text'}>
          {CONTENT[i % 2]}
        </span>,
        <CutSeparator key={`s-${i}`} />,
      ])}
    </div>
  )
}

export default function BrandMarquee() {
  return (
    <div className="brand-marquee" aria-hidden="true">
      <div className="brand-marquee-strip">
        <div className="brand-marquee-track">
          <MarqueeGroup />
          <MarqueeGroup />
        </div>
      </div>
    </div>
  )
}
