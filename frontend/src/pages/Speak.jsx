import { useCallback, useEffect, useRef, useState } from 'react'
import confetti from 'canvas-confetti'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import TopicDrum from '../components/TopicDrum'
import ReadyToSpeak from '../components/ReadyToSpeak'
import SpeakingNow from '../components/SpeakingNow'
import Countdown from '../components/Countdown'
import AiFeedback from '../components/AiFeedback'
import Feedback from '../components/Feedback'
import { topics as TOPICS } from '../data/topics'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import './Speak.css'

const DURATION = 60
const RESULT_TRANSITION_DELAY = 1500
const CONFETTI_COLORS = ['#ff4b1f', '#0c0b0a', '#ece0ce', '#ffffff']

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

function Speak({ onNavigate }) {
  const [stage, setStage] = useState('idle')
  const [picked, setPicked] = useState(null)
  const [timeLeft, setTimeLeft] = useState(DURATION)
  const [side, setSide] = useState(null)
  const [previous, setPrevious] = useState([])
  const [current, setCurrent] = useState(null)
  const { audioUrl, audioBlob, error, start, stop, analyserRef } = useAudioRecorder()
  const transitionTimeoutRef = useRef(null)

  useEffect(() => {
    return () => clearTimeout(transitionTimeoutRef.current)
  }, [])

  const newTopics = () => {
    clearTimeout(transitionTimeoutRef.current)
    setPicked(null)
    setPrevious([])
    setCurrent(null)
    setStage('idle')
  }

  // The drum sits on its landed topic for a beat before handing off — the
  // move to the "start speaking" page and the confetti fire together, right
  // as that page renders, not while the drum is still on screen.
  const confirmTopic = (topicIndex, topicSide) => {
    setPicked(topicIndex)
    setSide(topicSide)
    clearTimeout(transitionTimeoutRef.current)
    transitionTimeoutRef.current = setTimeout(() => {
      setStage('result')
      fireConfetti()
    }, RESULT_TRANSITION_DELAY)
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
    setStage('analysing')
  }, [stop])

  // The analysis screen owns the page while the backend works; the results
  // card only takes over once there is something to put in it. Both keep the
  // same <AiFeedback> mounted, so switching stage never restarts the request.
  const onFeedbackReady = useCallback((result) => {
    setCurrent(result)
    setStage('done')
  }, [])

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

  return (
    <main className="app">
      <SiteHeader onNavigate={onNavigate} />

      <div className="app-main">
        {stage === 'idle' && <TopicDrum duration={DURATION} onConfirm={confirmTopic} />}

        {stage === 'result' && (
          <ReadyToSpeak
            topic={TOPICS[picked]}
            side={side}
            duration={DURATION}
            error={error}
            onStart={() => setStage('countdown')}
            onChangeTopic={newTopics}
          />
        )}

        {stage === 'countdown' && <Countdown onDone={onCountdownDone} />}

        {stage === 'recording' && (
          <SpeakingNow
            topic={TOPICS[picked]}
            side={side}
            timeLeft={timeLeft}
            duration={DURATION}
            analyserRef={analyserRef}
            onFinish={finish}
          />
        )}

        {stage === 'analysing' && (
          <AiFeedback
            key={previous.length}
            topic={TOPICS[picked]}
            side={side}
            audioBlob={audioBlob}
            previous={previous[previous.length - 1]}
            onResult={onFeedbackReady}
          />
        )}

        {stage === 'done' && current && (
          <Feedback
            topic={TOPICS[picked]}
            side={side}
            data={current}
            audioUrl={audioUrl}
            downloadName={`argueitt-${slugify(TOPICS[picked])}-${side}-attempt${previous.length + 1}.${extensionFor(audioBlob)}`}
            previous={previous[previous.length - 1]}
            onRetry={retry}
            onNewTopic={newTopics}
          />
        )}
      </div>

      <SiteFooter />
    </main>
  )
}

export default Speak
