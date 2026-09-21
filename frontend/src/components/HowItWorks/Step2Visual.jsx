// Pipeline path is duplicated in App.css as the `offset-path` for the flowing
// dots — keep the two in sync if the node positions ever move.
const PIPE =
  'M50 78 C 66 78, 74 76, 92 76 C 116 76, 134 68, 158 68 L224 68 C 248 68, 266 76, 290 76 C 306 76, 316 78, 330 78'

const NODES = [
  { x: 92, y: 76, label: 'CHUNK' },
  { x: 158, y: 68, label: 'EMBED' },
  { x: 224, y: 68, label: 'RETRIEVE' },
  { x: 290, y: 76, label: 'LLM' },
]

const STATS = [
  ['128', 'CHUNKS'],
  ['1536', 'DIMENSIONS'],
  ['TOP-K 8', 'RETRIEVED'],
]

function NodeGlyph({ index, x, y }) {
  if (index === 0) {
    return (
      <g fill="#6f6b7c">
        <rect x={x - 7} y={y - 8} width="14" height="4" rx="1.2" />
        <rect x={x - 7} y={y - 2} width="14" height="4" rx="1.2" opacity="0.7" />
        <rect x={x - 7} y={y + 4} width="9" height="4" rx="1.2" opacity="0.45" />
      </g>
    )
  }
  if (index === 1) {
    return (
      <g fill="#6f6b7c">
        {[-5, 0, 5].map((dy) =>
          [-5, 0, 5].map((dx) => (
            <circle
              key={`${dx}:${dy}`}
              cx={x + dx}
              cy={y + dy}
              r="1.5"
              opacity={dx === 0 && dy === 0 ? 1 : 0.55}
            />
          )),
        )}
      </g>
    )
  }
  if (index === 2) {
    return (
      <g fill="none" stroke="#6f6b7c" strokeWidth="1.6" strokeLinecap="round">
        <circle cx={x - 1.5} cy={y - 1.5} r="5" />
        <path d={`M${x + 2.5} ${y + 2.5} L${x + 6} ${y + 6}`} />
      </g>
    )
  }
  return (
    <g>
      <path
        d={`M${x} ${y - 8} L${x + 7} ${y - 4} L${x + 7} ${y + 4} L${x} ${y + 8} L${x - 7} ${y + 4} L${x - 7} ${y - 4} Z`}
        fill="none"
        stroke="#7c3aed"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <circle cx={x} cy={y} r="2.2" fill="#7c3aed" />
    </g>
  )
}

export default function Step2Visual() {
  return (
    <div className="hiw-mock hiw-mock--pipe" aria-hidden="true">
      <svg viewBox="0 0 404 186" className="hiw-svg">
        <defs>
          <linearGradient id="hiwPipe" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#d5d0e4" />
            <stop offset="55%" stopColor="#a78bfa" />
            <stop offset="100%" stopColor="#7c3aed" />
          </linearGradient>
        </defs>

        {/* header strip */}
        <text x="2" y="16" className="hiw-t-cap">
          RETRIEVAL PIPELINE
        </text>
        <rect x="2" y="24" width="106" height="2" rx="1" fill="#e7e4ef" />
        <rect x="2" y="24" width="46" height="2" rx="1" fill="#7c3aed" />
        <circle cx="330" cy="12" r="3" fill="#7c3aed" className="hiw-pulse" />
        <text x="340" y="15" className="hiw-t-cap">
          PROCESSING
        </text>

        {/* source conversation */}
        <rect
          x="4"
          y="46"
          width="44"
          height="56"
          rx="4"
          fill="#fff"
          stroke="#ddd9e8"
          strokeWidth="1.2"
        />
        <path d="M38 46 L48 56 L38 56 Z" fill="#ece9f4" />
        {[56, 64, 72, 80, 88].map((y, i) => (
          <rect
            key={y}
            x="10"
            y={y}
            width={i % 2 ? 22 : 30}
            height="3"
            rx="1.5"
            fill="#ddd9e8"
          />
        ))}
        <text x="26" y="112" className="hiw-t-lab" textAnchor="middle">
          CHAT
        </text>

        {/* pipeline */}
        <path d={PIPE} fill="none" stroke="#ece9f4" strokeWidth="5" strokeLinecap="round" />
        <path
          d={PIPE}
          fill="none"
          stroke="url(#hiwPipe)"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeDasharray="4 4"
          className="hiw-pipe-dash"
        />

        {NODES.map((n, i) => (
          <g key={n.label}>
            <circle cx={n.x} cy={n.y} r="17" fill="#fff" stroke="#e2dfec" strokeWidth="1.2" />
            <circle
              cx={n.x}
              cy={n.y}
              r="17"
              fill="none"
              stroke="#7c3aed"
              strokeWidth="1.2"
              className={`hiw-node-ring hiw-node-ring--${i + 1}`}
            />
            <NodeGlyph index={i} x={n.x} y={n.y} />
            <text x={n.x} y="112" className="hiw-t-lab" textAnchor="middle">
              {n.label}
            </text>
          </g>
        ))}

        {/* flowing packets */}
        <circle r="2.6" fill="#7c3aed" className="hiw-pipe-dot hiw-pipe-dot--1" />
        <circle r="2.2" fill="#a78bfa" className="hiw-pipe-dot hiw-pipe-dot--2" />
        <circle r="1.8" fill="#c4b5fd" className="hiw-pipe-dot hiw-pipe-dot--3" />

        {/* structured output */}
        <rect
          x="336"
          y="44"
          width="64"
          height="60"
          rx="5"
          fill="#faf8ff"
          stroke="#d8cdf5"
          strokeWidth="1.2"
        />
        <rect x="342" y="50" width="30" height="4" rx="2" fill="#7c3aed" />
        {[60, 68, 76, 84, 92].map((y, i) => (
          <rect
            key={y}
            x="342"
            y={y}
            width={i % 2 ? 40 : 52}
            height="3"
            rx="1.5"
            fill="#ddd4f2"
          />
        ))}
        <text x="368" y="112" className="hiw-t-lab" textAnchor="middle">
          CONTEXT
        </text>

        {/* stat strip */}
        {STATS.map(([value, label], i) => (
          <g key={label}>
            <rect
              x={2 + i * 135}
              y="132"
              width="130"
              height="34"
              rx="5"
              fill="#f6f4fa"
              stroke="#e7e4ef"
              strokeWidth="1"
            />
            <text x={12 + i * 135} y="148" className="hiw-t-stat">
              {value}
            </text>
            <text x={12 + i * 135} y="159" className="hiw-t-lab">
              {label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}
