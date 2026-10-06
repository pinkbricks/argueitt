import { useEffect, useState } from 'react'
import { Clock, Square } from 'lucide-react'
import CookingPot from './CookingPot'
import './SpeakingNow.css'

const BAR_COUNT = 28

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// Samples the recorder's live AnalyserNode so the waveform reacts to actual
// voice instead of just animating decoratively. Runs its own rAF loop but
// throttles state updates — the analyser itself is polled every frame,
// React just doesn't need to re-render that often for a bar chart.
function useLiveLevels(analyserRef) {
  const [levels, setLevels] = useState(() => Array(BAR_COUNT).fill(0.08))

  useEffect(() => {
    let raf
    let lastUpdate = 0
    const data = new Uint8Array(32)

    const tick = (t) => {
      raf = requestAnimationFrame(tick)
      if (t - lastUpdate < 70) return
      lastUpdate = t
      const analyser = analyserRef.current
      if (!analyser) return
      analyser.getByteFrequencyData(data)
      setLevels(Array.from({ length: BAR_COUNT }, (_, i) => clamp(data[i % data.length] / 255, 0.06, 1)))
    }

    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [analyserRef])

  return levels
}

function SpeakingNow({ topic, side, timeLeft, duration, analyserRef, onFinish }) {
  const levels = useLiveLevels(analyserRef)
  const progress = clamp((duration - timeLeft) / duration, 0, 1)

  return (
    <section className="speaking">
      <div className="speaking-card">
        <span className="speaking-card-blob speaking-card-blob-a" aria-hidden="true" />
        <span className="speaking-card-blob speaking-card-blob-b" aria-hidden="true" />

        <div className="speaking-card-content">
          <p className="speaking-eyebrow">Your topic</p>
          <h1 className="speaking-topic">{topic}</h1>
          <span className={`speaking-pill speaking-pill-${side}`}>
            {side === 'for' ? 'For' : 'Against'}
          </span>

          <div className="speaking-timer-wrap">
            <span className="speaking-timer">{formatTime(timeLeft)}</span>
            <span className="speaking-timer-label">Time remaining</span>
          </div>

          <CookingPot fill={progress} />

          <p className="speaking-cook">Let me cook.</p>
          <p className="speaking-cook-sub">Your argument is being recorded.</p>

          <div className="speaking-wave" aria-hidden="true">
            {levels.map((level, i) => {
              const mid = (BAR_COUNT - 1) / 2
              const envelope = 1 - (Math.abs(i - mid) / mid) * 0.75
              return (
                <span
                  key={i}
                  className="speaking-wave-bar"
                  style={{ height: `${6 + level * envelope * 26}px`, opacity: 0.3 + envelope * 0.7 }}
                />
              )
            })}
          </div>
        </div>
      </div>

      <button type="button" className="speaking-stop-bar" onClick={onFinish}>
        <Square size={16} aria-hidden="true" fill="currentColor" />
        <span>Finish early</span>
        <span className="speaking-stop-divider" aria-hidden="true" />
        <Clock size={16} aria-hidden="true" />
        <span>{formatTime(timeLeft)}</span>
      </button>
    </section>
  )
}

export default SpeakingNow
