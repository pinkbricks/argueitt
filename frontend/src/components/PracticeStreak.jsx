import { useEffect, useState } from 'react'
import { Check, Flame, Trophy } from 'lucide-react'
import './PracticeStreak.css'

function dayLabel(day, options) {
  // These are calendar dates already resolved by the backend. Formatting in
  // UTC prevents another timezone conversion from moving them to yesterday.
  return new Intl.DateTimeFormat(undefined, { ...options, timeZone: 'UTC' })
    .format(new Date(`${day}T12:00:00Z`))
}

function PracticeStreak() {
  const [data, setData] = useState(null)
  const [state, setState] = useState('loading')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let controller
    let timer
    let disposed = false

    const refresh = async () => {
      controller?.abort()
      clearTimeout(timer)
      const request = new AbortController()
      controller = request
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
      try {
        const response = await fetch(`/api/streak?timezone=${encodeURIComponent(timezone)}`, {
          credentials: 'same-origin', signal: request.signal, cache: 'no-store',
        })
        if (!response.ok) throw new Error('Streak unavailable')
        const body = await response.json()
        if (disposed || request.signal.aborted) return
        setData(body)
        setState('ready')
      } catch {
        if (disposed || request.signal.aborted) return
        setState('error')
      } finally {
        if (!disposed && !request.signal.aborted) {
          const now = new Date()
          const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1)
          timer = setTimeout(refresh, midnight.getTime() - now.getTime() + 500)
        }
      }
    }
    const onVisible = () => { if (document.visibilityState === 'visible') refresh() }
    refresh()
    window.addEventListener('focus', refresh)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      disposed = true
      controller?.abort()
      clearTimeout(timer)
      window.removeEventListener('focus', refresh)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [retry])

  if (state !== 'ready') {
    return (
      <section className="practice-streak" aria-label="Daily practice streak">
        <p role="status">{state === 'loading' ? 'Loading your streak…' : 'Couldn’t load your streak. Your saved practice is still safe.'}</p>
        {state === 'error' && (
          <button className="streak-retry" onClick={() => { setState('loading'); setRetry((n) => n + 1) }}>Try again</button>
        )}
      </section>
    )
  }

  const message = data.practiced_today
    ? 'You showed up today. Come back tomorrow to keep it going.'
    : data.current_streak > 0
      ? 'Practise today to keep your streak going.'
      : data.total_practice_days > 0
        ? 'A fresh start is one practice away.'
        : 'Your first practice starts your streak.'

  return (
    <section className="practice-streak" aria-label="Daily practice streak">
      <div className="streak-heading">
        <div>
          <p className="streak-eyebrow"><Flame size={18} aria-hidden="true" /> Daily practice</p>
          <h2><strong>{data.current_streak}</strong> {data.current_streak === 1 ? 'day' : 'days'} in a row</h2>
        </div>
        <p className="streak-best"><Trophy size={16} aria-hidden="true" /> Best: {data.longest_streak} {data.longest_streak === 1 ? 'day' : 'days'}</p>
      </div>
      <p className="streak-message" role="status">{message}</p>
      <ol className="streak-week" aria-label="Practice over the last seven days">
        {data.week.map((day) => {
          const today = day.date === data.today
          const label = `${dayLabel(day.date, { weekday: 'long', month: 'long', day: 'numeric' })}: ${day.practiced ? 'practised' : 'not yet practised'}${today ? ', today' : ''}`
          return (
            <li key={day.date} className={`${day.practiced ? 'is-practiced' : ''} ${today ? 'is-today' : ''}`}
              aria-label={label} aria-current={today ? 'date' : undefined} title={label}>
              <span aria-hidden="true">{dayLabel(day.date, { weekday: 'short' })}</span>
              <span className="streak-day" aria-hidden="true">{day.practiced ? <Check size={18} /> : day.date.slice(-2)}</span>
            </li>
          )
        })}
      </ol>
      <p className="streak-note">One saved practice with speech counts each day. Days follow your local timezone.</p>
    </section>
  )
}

export default PracticeStreak
