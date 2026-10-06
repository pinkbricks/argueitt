import { useEffect, useState } from 'react'
import { Check } from 'lucide-react'
import CookingPot from './CookingPot'
import TipCard from './TipCard'
import './Analysing.css'

const CHECK_INTERVAL_MS = 4000

const CHECKS = [
  { id: 'clarity', label: 'Clarity', hint: 'Is your main point easy to follow?' },
  { id: 'structure', label: 'Structure', hint: 'Claim, reasons, evidence, conclusion' },
  { id: 'delivery', label: 'Delivery', hint: 'Pace, pauses and filler words' },
  { id: 'word-choice', label: 'Word choice', hint: 'Precision, variety and tone' },
]

// The backend reports two phases (transcribe, then analyse), not four, so the
// checklist walks forward on a cadence rather than on real per-check events.
// It deliberately stops on the last check and stays there: the fourth only
// completes when the actual result lands and this screen gives way, so the
// list can never sit at "all done" while the user is still waiting.
function useCheckProgress() {
  const [done, setDone] = useState(0)

  useEffect(() => {
    const id = setInterval(() => {
      setDone((n) => Math.min(n + 1, CHECKS.length - 1))
    }, CHECK_INTERVAL_MS)
    return () => clearInterval(id)
  }, [])

  return done
}

function CheckRow({ check, state }) {
  return (
    <li className={`check check-${state}`}>
      <span className="check-marker" aria-hidden="true">
        {state === 'done' && <Check size={14} strokeWidth={3} />}
      </span>

      <span className="check-text">
        <span className="check-label">{check.label}</span>
        <span className="check-hint">{check.hint}</span>
      </span>

      <span className="check-status">
        {state === 'active' && <span className="check-spinner" aria-hidden="true" />}
        {state === 'done' ? 'Done' : state === 'active' ? 'Analysing…' : 'Waiting…'}
      </span>
    </li>
  )
}

function Analysing({ topic, side }) {
  const done = useCheckProgress()

  return (
    <div className="analysing">
      <section className="analysing-main">
        <header className="analysing-head">
          <p className="analysing-eyebrow">Your topic</p>
          <h1 className="analysing-topic">“{topic}”</h1>
          <span className="analysing-side">
            Arguing {side === 'for' ? 'for' : 'against'}
          </span>
        </header>

        <div className="analysing-cook">
          <CookingPot fill={0.78} className="analysing-pot" />

          <div className="analysing-cook-copy">
            <h2 className="analysing-heading">
              Your argument
              <br />
              is cooking…
            </h2>
            <p className="analysing-sub">Your coach is analysing how you made your case.</p>
          </div>
        </div>

        <div className="analysing-checks">
          <ul className="check-list">
            {CHECKS.map((check, i) => (
              <CheckRow
                key={check.id}
                check={check}
                state={i < done ? 'done' : i === done ? 'active' : 'waiting'}
              />
            ))}
          </ul>

          <div className="analysing-progress">
            <div
              className="analysing-progress-track"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={CHECKS.length}
              aria-valuenow={done}
              aria-label="Analysis progress"
            >
              <span
                className="analysing-progress-fill"
                style={{ width: `${(done / CHECKS.length) * 100}%` }}
              />
            </div>
            <span className="analysing-progress-label">
              {done} of {CHECKS.length} checks done
            </span>
          </div>
        </div>
      </section>

      <TipCard eyebrow="While you wait" />
    </div>
  )
}

export default Analysing
