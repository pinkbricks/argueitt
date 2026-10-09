import { useMemo, useState } from 'react'
import {
  ArrowRight,
  AudioLines,
  CircleCheck,
  Download,
  Info,
  Mic,
  Pause,
  Sparkles,
  Target,
} from 'lucide-react'
import AudioPlayer from './AudioPlayer'
import PracticeStreak from './PracticeStreak'
import { buildHighlights } from '../utils/highlights'
import './Feedback.css'

const LEGEND = [
  { kind: 'filler', label: 'Filler word' },
  { kind: 'repetition', label: 'Repetition' },
  { kind: 'strong', label: 'Strong phrase' },
]

// The backend scores against SPONTANEOUS_ANSWER; these are its function ids.
const FUNCTION_LABELS = {
  coherence: 'Coherence',
  on_question: 'Answered the actual question',
  recovery: 'Recovery',
}

function fmt(n) {
  return Number.isInteger(n) ? n : Number(n).toFixed(1)
}

function delta(current, prev, lowerIsBetter = true) {
  if (prev == null) return null
  const d = Math.round((current - prev) * 10) / 10
  if (d === 0) return { text: 'same as last time', good: true }
  return {
    text: `${d > 0 ? '+' : ''}${d} vs last time`,
    good: lowerIsBetter ? d < 0 : d > 0,
  }
}

function Transcript({ tokens, showHighlights }) {
  return (
    <p className={`transcript-body${showHighlights ? '' : ' is-plain'}`}>
      {tokens.map((token, i) => {
        if (token.space) return <span key={i}>{token.text}</span>
        return (
          <span key={i}>
            <span className={token.kind && showHighlights ? `mark mark-${token.kind}` : undefined}>
              {token.text}
            </span>
            {token.pauseAfter && showHighlights && (
              <span className="mark-pause" title="Long pause">
                <Pause size={11} fill="currentColor" aria-hidden="true" />
              </span>
            )}
          </span>
        )
      })}
    </p>
  )
}

function Stat({ value, label, note }) {
  return (
    <div className="stat">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
      {note && <span className={`stat-delta ${note.good ? 'good' : 'bad'}`}>{note.text}</span>}
    </div>
  )
}

function Feedback({ topic, side, data, audioUrl, downloadName, previous, onRetry, onNewTopic }) {
  const [showHighlights, setShowHighlights] = useState(true)

  const metrics = data.delivery_metrics
  const transcript = data.transcript || ''

  const tokens = useMemo(
    () =>
      buildHighlights(transcript, {
        strongestMoment: data.strongest_moment,
        pauseDetails: metrics.pause_details,
      }),
    [transcript, data.strongest_moment, metrics.pause_details],
  )

  const weakest = data.functions[data.weakest_function_id]
  const worked = Object.entries(data.functions).filter(
    ([id, f]) => id !== data.weakest_function_id && f.score >= 2,
  )

  return (
    <div className="feedback">
      <header className="feedback-topic">
        <p className="feedback-eyebrow">Your topic</p>
        <h1 className="feedback-topic-text">“{topic}”</h1>
        <span className="feedback-side">Arguing {side === 'for' ? 'for' : 'against'}</span>
      </header>

      {data.persistence_status === 'saved' && <PracticeStreak key={data.attempt_id} />}

      {data.persistence_status === 'not_saved' && (
        <p className="feedback-saving" role="status">
          Your feedback is ready, but this attempt couldn’t be saved to your history.
          Keep this page open to review it and download your recording.
        </p>
      )}
      {data.persistence_status === 'guest' && (
        <p className="feedback-saving">This attempt is temporary. Sign in before your next attempt to save your progress.</p>
      )}

      <section className="feedback-transcript">
        <div className="feedback-transcript-head">
          <span className="feedback-transcript-title">
            <span className="feedback-icon-circle">
              <Mic size={16} aria-hidden="true" />
            </span>
            Your transcript
          </span>

          <button
            type="button"
            className={`highlight-toggle${showHighlights ? ' is-on' : ''}`}
            aria-pressed={showHighlights}
            onClick={() => setShowHighlights((on) => !on)}
          >
            <Sparkles size={14} aria-hidden="true" />
            {showHighlights ? 'Hide highlights' : 'Show highlights'}
          </button>
        </div>

        {transcript ? (
          <Transcript tokens={tokens} showHighlights={showHighlights} />
        ) : (
          <p className="transcript-body is-plain">No speech was detected in this recording.</p>
        )}

        {showHighlights && (
          <ul className="legend">
            {LEGEND.map(({ kind, label }) => (
              <li key={kind} className="legend-item">
                <span className={`legend-dot legend-dot-${kind}`} aria-hidden="true" />
                {label}
              </li>
            ))}
            <li className="legend-item">
              <Pause size={11} fill="currentColor" aria-hidden="true" />
              Pause
            </li>
          </ul>
        )}

        <div className="feedback-audio">
          {audioUrl ? (
            <>
              <AudioPlayer key={audioUrl} src={audioUrl} />
              <a className="feedback-download" href={audioUrl} download={downloadName}>
                <Download size={14} aria-hidden="true" />
                Download recording
              </a>
            </>
          ) : (
            <p className="feedback-saving">Saving your recording…</p>
          )}
        </div>
      </section>

      <section className="feedback-coach">
        <div className="delivery">
          <p className="panel-eyebrow dark">
            <AudioLines size={15} aria-hidden="true" />
            Your delivery
          </p>

          <div className="stats">
            <Stat
              value={metrics.filler_word_count}
              label="Filler words"
              note={delta(metrics.filler_word_count, previous?.delivery_metrics?.filler_word_count)}
            />
            <Stat value={Math.round(metrics.words_per_minute)} label="Words / min" />
            <Stat
              value={metrics.long_pause_count}
              label="Long pauses"
              note={delta(metrics.long_pause_count, previous?.delivery_metrics?.long_pause_count)}
            />
          </div>

          <p className="delivery-note">
            <Info size={14} aria-hidden="true" />
            Longest pause {fmt(metrics.longest_pause_sec)}s · first real word at{' '}
            {fmt(metrics.time_to_first_content_word_sec)}s
          </p>
        </div>

        <div className="opportunity">
          <p className="panel-eyebrow">
            <Target size={15} aria-hidden="true" />
            Your biggest opportunity
          </p>
          <h2 className="opportunity-headline">{weakest?.evidence || data.feedback_pointer}</h2>
          {weakest?.evidence && (
            <p className="opportunity-try">
              <strong>Try this:</strong> {data.feedback_pointer}
            </p>
          )}
        </div>

        <div className="worked">
          <p className="panel-eyebrow dark">
            <Sparkles size={15} aria-hidden="true" />
            What worked
          </p>
          <ul className="worked-list">
            {worked.length > 0 ? (
              worked.map(([id, f]) => (
                <li key={id}>
                  <CircleCheck size={16} aria-hidden="true" />
                  <span>
                    <strong>{FUNCTION_LABELS[id] || id}.</strong> {f.evidence}
                  </span>
                </li>
              ))
            ) : (
              <li>
                <CircleCheck size={16} aria-hidden="true" />
                <span>{data.strongest_moment}</span>
              </li>
            )}
          </ul>
        </div>

        <div className="next-focus">
          <p className="panel-eyebrow">
            <Target size={15} aria-hidden="true" />
            Next attempt, focus on
          </p>
          <p>{data.next_focus}</p>
        </div>

        <button type="button" className="feedback-retry" onClick={onRetry}>
          Try again
          <ArrowRight size={18} aria-hidden="true" />
        </button>

        <button type="button" className="feedback-new-topic" onClick={onNewTopic}>
          New topic
        </button>
      </section>
    </div>
  )
}

export default Feedback
