import { useEffect, useState } from 'react'
import { Lightbulb, Sparkles } from 'lucide-react'
import { waitingTips } from '../data/tips'
import './TipCard.css'

const TIP_INTERVAL_MS = 8000

// Starts somewhere random so a second attempt doesn't reopen on the same card,
// then cycles. The index comes back too — it keys the fade.
function useRotatingTip() {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * waitingTips.length))

  useEffect(() => {
    const id = setInterval(() => setIndex((i) => (i + 1) % waitingTips.length), TIP_INTERVAL_MS)
    return () => clearInterval(id)
  }, [])

  return [waitingTips[index], index]
}

// The quieter companion card, shared by the analysis screen and the error
// screen so both wait states read as the same product moment.
function TipCard({ eyebrow, heading = 'Did you know?' }) {
  const [{ fact, tip }, tipIndex] = useRotatingTip()

  return (
    <aside className="tipcard">
      <span className="tipcard-icon" aria-hidden="true">
        <Lightbulb size={22} />
      </span>

      <p className="tipcard-eyebrow">{eyebrow}</p>
      <h2 className="tipcard-heading">{heading}</h2>

      <div key={tipIndex} className="tipcard-body">
        <p className="tipcard-fact">{fact}</p>

        <div className="tipcard-tip">
          <p className="tipcard-tip-label">
            <Sparkles size={14} aria-hidden="true" />
            Tip
          </p>
          <p className="tipcard-tip-text">{tip}</p>
        </div>
      </div>

      <div className="tipcard-flourish" aria-hidden="true">
        <svg viewBox="0 0 60 60" className="tipcard-sprig">
          <path d="M30 56 Q30 30 44 12" />
          <path d="M30 40 Q16 38 10 26 Q24 24 30 40 Z" />
          <path d="M33 28 Q46 24 50 12 Q36 12 33 28 Z" />
        </svg>
        <p className="tipcard-flourish-text">Small changes, big impact.</p>
      </div>
    </aside>
  )
}

export default TipCard
