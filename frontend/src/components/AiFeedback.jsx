import { useEffect, useState } from 'react'

const SKIP_AI = true

const MOCK_TRANSCRIPT = "Um, so I think schools starting later would actually help students a lot. Teenagers naturally stay up later and their brains just aren't ready to learn at seven in the morning."

const MOCK_FEEDBACK = {
  score: 7,
  summary: 'Mock feedback — AI calls are disabled while testing.',
  filler_count: 2,
  filler_breakdown: [{ word: 'um', count: 1 }, { word: 'so', count: 1 }],
  time_to_first_point_seconds: 2.5,
  first_point: 'Schools starting later would actually help students a lot.',
  structure: [
    { part: 'Opening', present: true, note: 'Mock note.' },
    { part: 'Position', present: true, note: 'Mock note.' },
    { part: 'Supporting points', present: false, note: 'Mock note.' },
    { part: 'Conclusion', present: false, note: 'Mock note.' },
  ],
  structure_summary: 'Mock structure summary.',
  strengths: ['Mock strength one.'],
  improvements: ['Mock improvement one.'],
  counter_argument: 'Mock counter-argument.',
  stronger_opening: 'Mock stronger opening.',
}

function fmt(n) {
  return Number.isInteger(n) ? n : n.toFixed(1)
}

function change(cur, prev, lowerIsBetter = true) {
  if (prev == null) return null
  const d = Math.round((cur - prev) * 10) / 10
  if (d === 0) return { text: 'same as last time', good: true }
  return { text: `${d > 0 ? '+' : ''}${d} vs last time`, good: lowerIsBetter ? d < 0 : d > 0 }
}

function Tile({ label, value, note, delta }) {
  return (
    <div className="tile">
      <span className="tile-label">{label}</span>
      <span className="tile-value">{value}</span>
      {note && <span className="tile-note">{note}</span>}
      {delta && <span className={`tile-delta ${delta.good ? 'good' : 'bad'}`}>{delta.text}</span>}
    </div>
  )
}

function AiFeedback({ topic, side, audioBlob, previous, onResult }) {
  const [status, setStatus] = useState('transcribing')
  const [transcript, setTranscript] = useState('')
  const [data, setData] = useState(null)

  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!audioBlob) return
    let cancelled = false

    if (SKIP_AI) {
      ;(async () => {
        setTranscript(MOCK_TRANSCRIPT)
        setStatus('analysing')
        await new Promise((r) => setTimeout(r, 300))
        if (cancelled) return
        setData(MOCK_FEEDBACK)
        onResult(MOCK_FEEDBACK)
        setStatus('done')
      })()
      return () => {
        cancelled = true
      }
    }

    const post = async (url, fields) => {
      const form = new FormData()
      Object.entries(fields).forEach(([k, v]) => form.append(k, v))
      form.append('audio', audioBlob, 'speech.wav')
      const res = await fetch(url, { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      return res.json()
    }
    ;(async () => {
      try {
        const saved = await post('/api/transcribe', { topic, side })
        if (cancelled) return
        setTranscript(saved.transcript)
        setStatus('analysing')
        const json = await post('/api/analyze', { transcript_id: saved.id })
        if (cancelled) return
        setData(json)
        onResult(json)
        setStatus('done')
      } catch {
        if (!cancelled) setStatus('error')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [topic, side, audioBlob, onResult, attempt])

  const retry = () => {
    setStatus('transcribing')
    setAttempt((n) => n + 1)
  }

  if (status === 'error') {
    return (
      <div className="ai-cta">
        <p className="error">Couldn't analyse your speech. Is the backend running?</p>
        <button className="btn ghost" onClick={retry}>Try again</button>
      </div>
    )
  }

  if (status !== 'done' || !data) {
    return (
      <div className="ai-cta">
        <p className="hint">
          {status === 'transcribing'
            ? 'Step 1 of 2: transcribing your recording…'
            : 'Step 2 of 2: your coach is analysing it…'}
        </p>
        {transcript && (
          <details className="transcript" open>
            <summary>Transcript</summary>
            <p>{transcript}</p>
          </details>
        )}
      </div>
    )
  }

  return (
    <div className="ai">
      <div className="ai-head">
        <span className="ai-score">{data.score}<small>/10</small></span>
        <p>{data.summary}</p>
      </div>

      <div className="tiles">
        <Tile
          label="Filler words"
          value={data.filler_count}
          delta={change(data.filler_count, previous?.filler_count)}
        />
        <Tile
          label="Time to first point"
          value={`${fmt(data.time_to_first_point_seconds)}s`}
          delta={change(data.time_to_first_point_seconds, previous?.time_to_first_point_seconds)}
        />
      </div>

      {data.filler_breakdown.length > 0 && (
        <p className="fillers">
          {data.filler_breakdown.map((f) => (
            <span key={f.word} className="chip">{f.word} × {f.count}</span>
          ))}
        </p>
      )}

      <h3>First point</h3>
      <p className="ai-quote">{data.first_point}</p>

      <h3>Structure</h3>
      <ul className="structure">
        {data.structure.map((p) => (
          <li key={p.part} className={p.present ? 'yes' : 'no'}>
            <strong>{p.part}</strong>
            <span>{p.note}</span>
          </li>
        ))}
      </ul>
      <p>{data.structure_summary}</p>

      <h3>What worked</h3>
      <ul>{data.strengths.map((t) => <li key={t}>{t}</li>)}</ul>

      <h3>How to improve</h3>
      <ul>{data.improvements.map((t) => <li key={t}>{t}</li>)}</ul>

      <h3>What your opponent would say</h3>
      <p>{data.counter_argument}</p>

      <h3>A stronger opening</h3>
      <p className="ai-quote">{data.stronger_opening}</p>

      <details className="transcript">
        <summary>Transcript</summary>
        <p>{transcript || 'No speech detected.'}</p>
      </details>
    </div>
  )
}

export default AiFeedback
