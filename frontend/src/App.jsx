import { useCallback, useEffect, useRef, useState } from 'react'
import confetti from 'canvas-confetti'
import Wheel from './components/Wheel'
import Countdown from './components/Countdown'
import AiFeedback from './components/AiFeedback'
import { topics as TOPICS } from './data/topics'
import { useAudioRecorder } from './hooks/useAudioRecorder'
import './App.css'

const DURATION = 60
const WHEEL_SLICES = 10
const SLICE = 360 / WHEEL_SLICES
const CONFETTI_COLORS = ['#7068BF', '#F19ABE', '#918BDF', '#FAFCFE']

function fireConfetti() {
  const base = { colors: CONFETTI_COLORS, ticks: 220, scalar: 1.1 }
  confetti({ ...base, particleCount: 90, spread: 80, origin: { y: 0.6 } })
  confetti({ ...base, particleCount: 50, angle: 60, spread: 60, origin: { x: 0, y: 0.7 } })
  confetti({ ...base, particleCount: 50, angle: 120, spread: 60, origin: { x: 1, y: 0.7 } })
}

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40) || 'argueitt'
}

function extensionFor(blob) {
  const mime = (blob?.type || '').split(';')[0]
  if (mime === 'audio/mp4') return 'm4a'
  if (mime === 'audio/ogg') return 'ogg'
  if (mime === 'audio/wav') return 'wav'
  return 'webm'
}

function shuffle(items) {
  const a = [...items]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function SideTag({ side, large }) {
  return (
    <p className={`side ${side}${large ? ' large' : ''}`}>
      You argue <strong>{side === 'for' ? 'FOR' : 'AGAINST'}</strong>
    </p>
  )
}

function App() {
  const [stage, setStage] = useState('idle')
  const [rotation, setRotation] = useState(0)
  const [picked, setPicked] = useState(null)
  const [timeLeft, setTimeLeft] = useState(DURATION)
  const [side, setSide] = useState(null)
  const [previous, setPrevious] = useState([])
  const [current, setCurrent] = useState(null)
  const { audioUrl, audioBlob, error, start, stop } = useAudioRecorder()
  const pickedRef = useRef(null)

  const spin = () => {
    const slice = Math.floor(Math.random() * WHEEL_SLICES)
    const target = slice * SLICE + 4 + Math.random() * (SLICE - 8)
    const delta = (((-target - rotation) % 360) + 360) % 360
    pickedRef.current = shuffle(TOPICS.map((_, i) => i))[slice]
    setPicked(null)
    setPrevious([])
    setCurrent(null)
    setStage('spinning')
    setRotation(rotation + 360 * 5 + delta)
  }

  const onSpinEnd = () => {
    if (stage !== 'spinning') return
    setPicked(pickedRef.current)
    setSide(Math.random() < 0.5 ? 'for' : 'against')
    setStage('result')
    fireConfetti()
  }

  const onCountdownDone = useCallback(async () => {
    const ok = await start()
    if (ok) {
      setTimeLeft(DURATION)
      setStage('recording')
    } else {
      setStage('result')
    }
  }, [start])

  const finish = useCallback(() => {
    stop()
    setStage('done')
  }, [stop])

  useEffect(() => {
    if (stage !== 'recording') return
    const end = Date.now() + DURATION * 1000
    const id = setInterval(() => {
      const left = Math.max(0, Math.ceil((end - Date.now()) / 1000))
      setTimeLeft(left)
      if (left === 0) finish()
    }, 200)
    return () => clearInterval(id)
  }, [stage, finish])

  const retry = () => {
    if (current) setPrevious((p) => [...p, current])
    setCurrent(null)
    setStage('countdown')
  }

  const showWheel = stage === 'idle' || stage === 'spinning'

  return (
    <main className="app">
      <header>
        <h1 className="logo">Argueitt</h1>
        {showWheel && (
          <p className="tagline">Spin the wheel. Pick a topic. Argue your case.</p>
        )}
      </header>

      {showWheel && (
        <>
          <Wheel
            rotation={rotation}
            spinning={stage === 'spinning'}
            onTransitionEnd={onSpinEnd}
          />
          <button className="btn primary" onClick={spin} disabled={stage === 'spinning'}>
            {stage === 'spinning' ? 'Spinning…' : 'Spin the Wheel'}
          </button>
        </>
      )}

      {stage === 'result' && (
        <section className="topic">
          <p className="topic-label">Your topic</p>
          <h2>{TOPICS[picked]}</h2>
          <SideTag side={side} large />
          <p className="hint">You have 60 seconds. You don't get a say in the side, so make it count.</p>
          {error && <p className="error">{error}</p>}
          <div className="actions">
            <button className="btn primary" onClick={() => setStage('countdown')}>
              Start speaking
            </button>
            <button className="btn ghost" onClick={() => setStage('idle')}>
              Spin again
            </button>
          </div>
        </section>
      )}

      {stage === 'countdown' && <Countdown onDone={onCountdownDone} />}

      {stage === 'recording' && (
        <section className="card center">
          <h2>{TOPICS[picked]}</h2>
          <SideTag side={side} />
          <div className="timer">{timeLeft}</div>
          <div className="rec">
            <span className="rec-dot" /> Recording
          </div>
          <button className="btn ghost" onClick={finish}>
            Finish early
          </button>
        </section>
      )}

      {stage === 'done' && (
        <section className="card done">
          <span className="badge">Attempt {previous.length + 1}</span>
          <h2>{TOPICS[picked]}</h2>
          <SideTag side={side} />
          {audioUrl ? (
            <>
              <audio controls src={audioUrl} />
              <a
                className="btn ghost"
                href={audioUrl}
                download={`argueitt-${slugify(TOPICS[picked])}-${side}-attempt${previous.length + 1}.${extensionFor(audioBlob)}`}
              >
                Download recording
              </a>
            </>
          ) : (
            <p className="hint">Saving your recording…</p>
          )}
          <AiFeedback
            key={previous.length}
            topic={TOPICS[picked]}
            side={side}
            audioBlob={audioBlob}
            previous={previous[previous.length - 1]}
            onResult={setCurrent}
          />
          <div className="actions">
            <button className="btn primary" onClick={retry}>
              Try this topic again
            </button>
            <button className="btn ghost" onClick={() => setStage('idle')}>
              New topic
            </button>
          </div>
        </section>
      )}
    </main>
  )
}

export default App
