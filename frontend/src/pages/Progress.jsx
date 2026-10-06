import { useEffect, useState } from 'react'
import { CalendarDays, ChevronDown, Target } from 'lucide-react'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import { useSession } from '../hooks/useSession'
import './Progress.css'

function formatDate(iso) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function round(value) {
  return Number.isFinite(value) ? Math.round(value) : 0
}

function Attempt({ attempt }) {
  const { analysis } = attempt
  const metrics = analysis?.delivery_metrics
  const weakest = analysis?.functions?.[analysis?.weakest_function_id]

  return (
    <li className="attempt">
      <div className="attempt-head">
        <span className="attempt-date">
          <CalendarDays size={14} aria-hidden="true" />
          {formatDate(attempt.created_at)}
        </span>
        <span className={`attempt-side attempt-side-${attempt.side}`}>
          Arguing {attempt.side === 'for' ? 'for' : 'against'}
        </span>
      </div>

      <h2 className="attempt-topic">“{attempt.topic}”</h2>

      {analysis ? (
        <>
          {analysis.next_focus && (
            <p className="attempt-focus">
              <Target size={15} aria-hidden="true" />
              <span>{analysis.next_focus}</span>
            </p>
          )}

          {metrics && (
            <ul className="attempt-metrics">
              <li>
                <strong>{metrics.filler_word_count ?? 0}</strong> filler words
              </li>
              <li>
                <strong>{round(metrics.words_per_minute)}</strong> words / min
              </li>
              <li>
                <strong>{metrics.long_pause_count ?? 0}</strong> long pauses
              </li>
            </ul>
          )}

          <details className="attempt-more">
            <summary>
              Full feedback
              <ChevronDown size={15} aria-hidden="true" />
            </summary>

            <div className="attempt-more-body">
              {weakest?.evidence && (
                <section>
                  <h3>Your biggest opportunity</h3>
                  <p>{weakest.evidence}</p>
                </section>
              )}

              {analysis.feedback_pointer && (
                <section>
                  <h3>How to improve</h3>
                  <p>{analysis.feedback_pointer}</p>
                </section>
              )}

              {analysis.strongest_moment && (
                <section>
                  <h3>Strongest moment</h3>
                  <p className="attempt-quote">{analysis.strongest_moment}</p>
                </section>
              )}

              {attempt.transcript && (
                <section>
                  <h3>What you said</h3>
                  <p className="attempt-quote">{attempt.transcript}</p>
                </section>
              )}
            </div>
          </details>
        </>
      ) : (
        <p className="attempt-unanalysed">
          This one was recorded but never analysed.
        </p>
      )}
    </li>
  )
}

function Progress({ onNavigate }) {
  const { user, status } = useSession()
  const [attempts, setAttempts] = useState([])
  const [state, setState] = useState('loading')

  useEffect(() => {
    if (status !== 'ready' || !user) return undefined
    let cancelled = false

    fetch('/api/attempts', { credentials: 'same-origin' })
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((body) => {
        if (cancelled) return
        setAttempts(body.attempts || [])
        setState('ready')
      })
      .catch(() => {
        if (!cancelled) setState('error')
      })

    return () => {
      cancelled = true
    }
  }, [status, user])

  const analysed = attempts.filter((a) => a.analysis)

  return (
    <main className="app">
      <SiteHeader onNavigate={onNavigate} />

      <div className="progress-main">
        <header className="progress-head">
          <p className="progress-eyebrow">Your progress</p>
          <h1 className="progress-title">Everything you&apos;ve argued.</h1>
          {status === 'ready' && user && state === 'ready' && (
            <p className="progress-count">
              {attempts.length} {attempts.length === 1 ? 'attempt' : 'attempts'}
              {analysed.length !== attempts.length && ` · ${analysed.length} analysed`}
            </p>
          )}
        </header>

        {status !== 'ready' ? null : !user ? (
          <section className="progress-empty">
            <p>Sign in to keep a record of what you&apos;ve argued and how it went.</p>
            <a
              className="progress-cta"
              href="/sign-in"
              onClick={(event) => {
                event.preventDefault()
                onNavigate('/sign-in')
              }}
            >
              Sign in
            </a>
          </section>
        ) : state === 'loading' ? (
          <p className="progress-status">Loading your attempts…</p>
        ) : state === 'error' ? (
          <p className="progress-status">
            Couldn&apos;t load your attempts. Is the backend running?
          </p>
        ) : attempts.length === 0 ? (
          <section className="progress-empty">
            <p>No attempts yet. Your first one will show up here.</p>
            <a
              className="progress-cta"
              href="/speak"
              onClick={(event) => {
                event.preventDefault()
                onNavigate('/speak')
              }}
            >
              Start speaking
            </a>
          </section>
        ) : (
          <ul className="attempt-list">
            {attempts.map((attempt) => (
              <Attempt key={attempt.id} attempt={attempt} />
            ))}
          </ul>
        )}
      </div>

      <SiteFooter />
    </main>
  )
}

export default Progress
