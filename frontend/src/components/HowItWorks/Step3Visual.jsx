const CONTENTS = [
  ['01', 'OVERVIEW', 96],
  ['02', 'KEY DECISIONS', 118],
  ['03', 'PROBLEMS & SOLUTIONS', 140],
  ['04', 'TECHNICAL DECISIONS', 128],
]

function Thumb({ x, y }) {
  return (
    <g>
      <rect
        x={x}
        y={y}
        width="46"
        height="24"
        rx="3"
        fill="#eef0f6"
        stroke="#dcd8e6"
        strokeWidth="0.9"
      />
      <path
        d={`M${x + 5} ${y + 19} L${x + 15} ${y + 9} L${x + 23} ${y + 17} L${x + 29} ${y + 11} L${x + 41} ${y + 19} Z`}
        fill="#c9c3dc"
      />
      <circle cx={x + 34} cy={y + 8} r="2.6" fill="#d9d3ea" />
    </g>
  )
}

export default function Step3Visual() {
  return (
    <div className="hiw-mock hiw-mock--pdf" aria-hidden="true">
      <svg viewBox="0 0 404 186" className="hiw-svg">
        <g className="hiw-pdf-float">
          {/* stacked pages behind */}
          <rect
            x="16"
            y="14"
            width="172"
            height="168"
            rx="6"
            fill="#eceaf2"
            stroke="#ddd9e8"
            strokeWidth="1"
          />
          <rect
            x="10"
            y="9"
            width="172"
            height="173"
            rx="6"
            fill="#f5f3f9"
            stroke="#ddd9e8"
            strokeWidth="1"
          />

          {/* front page */}
          <rect
            x="4"
            y="4"
            width="172"
            height="178"
            rx="6"
            fill="#fff"
            stroke="#d9d5e6"
            strokeWidth="1.2"
          />
          <path d="M4 10 a6 6 0 0 1 6-6 h160 a6 6 0 0 1 6 6 v2 H4 Z" fill="#7c3aed" />

          <text x="14" y="26" className="hiw-t-doc">
            MEMORY EXPORT
          </text>
          <text x="14" y="35" className="hiw-t-meta">
            RAG PIPELINE · 24 MSGS · 2026-09-18
          </text>
          <rect x="14" y="40" width="148" height="1" fill="#eae7f1" />

          <text x="14" y="53" className="hiw-t-sec">
            01 OVERVIEW
          </text>
          {[58, 64, 70].map((y, i) => (
            <rect
              key={y}
              x="14"
              y={y}
              width={i === 2 ? 96 : 148}
              height="3.2"
              rx="1.6"
              fill="#e4e1ec"
            />
          ))}

          <text x="14" y="88" className="hiw-t-sec">
            04 TECHNICAL DECISIONS
          </text>
          <rect x="14" y="93" width="148" height="42" rx="4" fill="#17151f" />
          <text x="20" y="104" className="hiw-t-code">
            chunk_size = 800
          </text>
          <text x="20" y="114" className="hiw-t-code hiw-t-code--accent">
            store = Chroma(embed)
          </text>
          <rect x="20" y="119" width="64" height="2.6" rx="1.3" fill="#4c4467" />
          <rect x="88" y="119" width="30" height="2.6" rx="1.3" fill="#7c3aed" opacity="0.8" />
          <rect x="20" y="126" width="44" height="2.6" rx="1.3" fill="#3b3550" />
          <rect x="68" y="126" width="52" height="2.6" rx="1.3" fill="#4c4467" />

          <text x="14" y="152" className="hiw-t-sec">
            IMAGES FROM CONVERSATION
          </text>
          <Thumb x={14} y={156} />
          <Thumb x={65} y={156} />
          <Thumb x={116} y={156} />
        </g>

        {/* contents index */}
        <text x="198" y="15" className="hiw-t-cap">
          DOCUMENT CONTENTS
        </text>
        <rect x="198" y="21" width="204" height="1" fill="#e7e4ef" />

        {CONTENTS.map(([num, label, bar], i) => {
          const y = 32 + i * 26
          return (
            <g key={num}>
              <rect x="198" y={y} width="19" height="14" rx="3.5" fill="#f1ecfd" />
              <text x="207.5" y={y + 10} className="hiw-t-num" textAnchor="middle">
                {num}
              </text>
              <text x="224" y={y + 10} className="hiw-t-row">
                {label}
              </text>
              <rect x="224" y={y + 15} width={bar} height="2.6" rx="1.3" fill="#e7e4ef" />
              <rect
                x="224"
                y={y + 15}
                width={bar * 0.42}
                height="2.6"
                rx="1.3"
                fill="#c4b5fd"
              />
            </g>
          )
        })}

        {/* handoff badge */}
        <rect
          x="198"
          y="142"
          width="150"
          height="26"
          rx="13"
          fill="#f6f2ff"
          stroke="#d8cdf5"
          strokeWidth="1"
        />
        <circle cx="213" cy="155" r="6.5" fill="#7c3aed" />
        <path
          d="M210 155 l2.2 2.4 l4-4.6"
          fill="none"
          stroke="#fff"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <text x="225" y="158" className="hiw-t-row">
          READY FOR HANDOFF
        </text>
        <text x="358" y="158" className="hiw-t-lab">
          4 PAGES
        </text>
      </svg>
    </div>
  )
}
