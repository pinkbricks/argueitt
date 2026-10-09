import { useEffect, useState } from 'react'
import { CalendarDays, ChevronDown, Target } from 'lucide-react'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import PracticeStreak from '../components/PracticeStreak'
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
  // Remount history when the account changes so another account's data never
  // appears while its first page is loading.
  return <ProgressHistory key={user?.id || 'guest'} user={user} status={status} onNavigate={onNavigate} />
}

function ProgressHistory({ user, status, onNavigate }) {
  const [attempts, setAttempts] = useState([])
  const [state, setState] = useState('loading')
  const [nextCursor, setNextCursor] = useState(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const [moreError, setMoreError] = useState(false)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    if (status !== 'ready' || !user) return undefined
    const controller = new AbortController()

    fetch('/api/attempts', { credentials: 'same-origin', signal: controller.signal })
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((body) => {
        if (controller.signal.aborted) return
        setAttempts(body.attempts || [])
        setNextCursor(body.next_cursor)
        setState('ready')
      })
      .catch(() => {
        if (!controller.signal.aborted) setState('error')
      })

    return () => controller.abort()
  }, [status, user, reload])

  const loadMore = async () => {
    if (loadingMore || !nextCursor) return
    setLoadingMore(true)
    setMoreError(false)
    try {
      const res = await fetch(`/api/attempts?cursor=${encodeURIComponent(nextCursor)}`, { credentials: 'same-origin' })
      if (!res.ok) throw new Error('History unavailable')
      const body = await res.json()
      setAttempts((current) => {
        const ids = new Set(current.map((attempt) => attempt.id))
        return [...current, ...body.attempts.filter((attempt) => !ids.has(attempt.id))]
      })
      setNextCursor(body.next_cursor)
    } catch {
      setMoreError(true)
    } finally {
      setLoadingMore(false)
    }
  }

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
              {attempts.length} {attempts.length === 1 ? 'attempt' : 'attempts'}{nextCursor ? ' loaded' : ''}
              {analysed.length !== attempts.length && ` · ${analysed.length} analysed`}
            </p>
          )}
        </header>

        {status === 'ready' && user && <PracticeStreak />}

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
          <div className="progress-status" role="status">
            <p>Couldn&apos;t load your attempts. Please try again.</p>
            <button className="progress-cta" onClick={() => { setState('loading'); setReload((n) => n + 1) }}>Try again</button>
          </div>
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
          <>
            <ul className="attempt-list">
              {attempts.map((attempt) => (
                <Attempt key={attempt.id} attempt={attempt} />
              ))}
            </ul>
            {moreError && <p className="progress-status" role="status">Couldn’t load more attempts. Please try again.</p>}
            {nextCursor && (
              <button className="progress-cta" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? 'Loading…' : 'Load more'}
              </button>
            )}
          </>

        )}
      </div>

      <SiteFooter />
    </main>
  )
}

export default Progress
