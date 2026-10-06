import { Mic, AudioLines, RefreshCw } from 'lucide-react'
import './ReadyToSpeak.css'

function ReadyToSpeak({ topic, side, duration, error, onStart, onChangeTopic }) {
  return (
    <section className="ready">
      <div className="ready-eyebrow">
        <span className="ready-eyebrow-tick" aria-hidden="true" />
        <p>Your topic</p>
      </div>

      <h1 className="ready-topic">{topic}</h1>

      <span className={`ready-pill ready-pill-${side}`}>
        {side === 'for' ? 'Argue For' : 'Argue Against'}
      </span>

      <div className="ready-card-wrap">
        <span className="ready-card-blob ready-card-blob-a" aria-hidden="true" />
        <span className="ready-card-blob ready-card-blob-b" aria-hidden="true" />
        <div className="ready-card">
          <span className="ready-mic-glow" aria-hidden="true" />
          <span className="ready-mic" aria-hidden="true">
            <Mic size={22} />
          </span>
          <h2>Ready when you are</h2>
          <p>Speak for {duration} seconds, then get an analysis of your performance.</p>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <button type="button" className="ready-cta" onClick={onStart}>
        <AudioLines aria-hidden="true" size={18} />
        <span>Start speaking</span>
      </button>

      <button type="button" className="ready-change" onClick={onChangeTopic}>
        <RefreshCw aria-hidden="true" size={14} />
        <span>You can change your topic anytime.</span>
      </button>
    </section>
  )
}

export default ReadyToSpeak
