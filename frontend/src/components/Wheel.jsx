const COUNT = 10
const SLICE = 360 / COUNT
const SIZE = 400
const R = SIZE / 2
const INNER = R - 16
const PURPLE = '#7068BF'
const PINK = '#F19ABE'
const LIGHT = '#E4E4FF'

function polar(angleDeg, radius) {
  const a = ((angleDeg - 90) * Math.PI) / 180
  return [R + radius * Math.cos(a), R + radius * Math.sin(a)]
}

function Wheel({ rotation, spinning, onTransitionEnd }) {
  return (
    <div className="wheel-wrap">
      <svg className="wheel-pointer" viewBox="0 0 40 36" aria-hidden="true">
        <path d="M2 2 H38 L20 34 Z" fill={PURPLE} stroke={LIGHT} strokeWidth="3" strokeLinejoin="round" />
      </svg>
      <svg
        className="wheel"
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        style={{
          transform: `rotate(${rotation}deg)`,
          transition: spinning
            ? 'transform 5s cubic-bezier(0.12, 0.6, 0.1, 1)'
            : 'none',
        }}
        onTransitionEnd={onTransitionEnd}
      >
        <circle cx={R} cy={R} r={R - 1} fill={PURPLE} stroke={PINK} strokeWidth="2" />
        {Array.from({ length: COUNT }, (_, i) => {
          const start = i * SLICE
          const end = start + SLICE
          const [x1, y1] = polar(start, INNER)
          const [x2, y2] = polar(end, INNER)
          const [tx, ty] = polar(start + SLICE / 2, INNER * 0.72)
          const purple = i % 2 === 0
          return (
            <g key={i}>
              <path
                d={`M${R},${R} L${x1},${y1} A${INNER},${INNER} 0 0 1 ${x2},${y2} Z`}
                fill={purple ? PURPLE : PINK}
                stroke={LIGHT}
                strokeWidth="2.5"
              />
              <text
                x={tx}
                y={ty}
                className="wheel-num"
                fill={purple ? LIGHT : PURPLE}
                transform={`rotate(${start + SLICE / 2} ${tx} ${ty})`}
              >
                {i + 1}
              </text>
            </g>
          )
        })}
        <circle cx={R} cy={R} r="42" fill={LIGHT} stroke={PURPLE} strokeWidth="5" />
        <circle cx={R} cy={R} r="12" fill={PURPLE} />
      </svg>
    </div>
  )
}

export default Wheel
