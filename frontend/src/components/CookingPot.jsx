import { useId } from 'react'
import './CookingPot.css'

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

// A wavy-topped liquid fill instead of a plain rect — `fillHeight` is how
// tall the liquid is, in the pot's own coordinate space.
function liquidPath(fillHeight) {
  const bottom = 108
  const top = bottom - fillHeight
  const left = 22
  const right = 118
  return `M${left} ${bottom} L${left} ${top + 4} Q${left + 24} ${top - 4} ${left + 48} ${top} Q${left + 72} ${top + 4} ${left + 96} ${top - 2} L${right} ${top + 4} L${right} ${bottom} Z`
}

// Shared between the recording screen (where `fill` tracks elapsed time) and
// the analysis screen (where the pot is simply at a boil). `useId` keeps the
// clip/gradient ids unique, since the defs are per-instance.
function CookingPot({ fill = 0.5, className = '' }) {
  const rawId = useId().replace(/:/g, '')
  const clipId = `pot-clip-${rawId}`
  const gradientId = `pot-liquid-${rawId}`
  const fillHeight = 16 + clamp(fill, 0, 1) * 64

  return (
    <div className={`pot-scene ${className}`.trim()} aria-hidden="true">
      <span className="pot-steam pot-steam-a" />
      <span className="pot-steam pot-steam-b" />
      <span className="pot-steam pot-steam-c" />

      <svg className="pot" viewBox="0 0 140 120">
        <defs>
          <clipPath id={clipId}>
            <path d="M24 22 H116 L106 104 Q102 110 96 110 H44 Q38 110 34 104 Z" />
          </clipPath>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ff9a63" />
            <stop offset="100%" stopColor="#e0341a" />
          </linearGradient>
        </defs>

        <g clipPath={`url(#${clipId})`}>
          <path className="pot-liquid" d={liquidPath(fillHeight)} fill={`url(#${gradientId})`} />
          <circle className="pot-bubble pot-bubble-1" cx="52" cy="92" r="3" />
          <circle className="pot-bubble pot-bubble-2" cx="68" cy="98" r="2.2" />
          <circle className="pot-bubble pot-bubble-3" cx="82" cy="90" r="2.6" />
          <circle className="pot-bubble pot-bubble-4" cx="60" cy="82" r="2" />
          <circle className="pot-bubble pot-bubble-5" cx="92" cy="99" r="1.8" />
        </g>

        <path
          className="pot-outline"
          d="M24 22 H116 L106 104 Q102 110 96 110 H44 Q38 110 34 104 Z"
        />

        <g className="pot-lid">
          <path className="pot-handle" d="M58 22 Q70 4 82 22" />
          <line className="pot-rim" x1="16" y1="22" x2="124" y2="22" />
        </g>
      </svg>

      <div className="pot-flames">
        {Array.from({ length: 5 }).map((_, i) => (
          <span key={i} className="pot-flame" />
        ))}
      </div>
    </div>
  )
}

export default CookingPot
