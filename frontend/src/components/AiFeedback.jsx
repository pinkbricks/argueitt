import { useEffect, useState } from 'react'
import Analysing from './Analysing'
import AnalysisError from './AnalysisError'

// A recording keeps its request ID across retries and effect remounts.
const recordingIds = new WeakMap()
function requestIdFor(blob) {
  if (!recordingIds.has(blob)) recordingIds.set(blob, crypto.randomUUID())
  return recordingIds.get(blob)
}

const SKIP_AI = false

const MOCK_TRANSCRIPT = "Um, so I think schools starting later would actually help students a lot. Teenagers naturally stay up later and their brains just aren't ready to learn at seven in the morning."

const MOCK_FEEDBACK = {
  challenge_type: 'answer_the_unexpected',
  framework_name: 'SPONTANEOUS_ANSWER',
  model_version: 'mock',
  functions: {
    coherence: { evidence: 'Schools starting later would actually help students a lot.', score: 2 },
    on_question: { evidence: 'Teenagers naturally stay up later...', score: 2 },
    recovery: { evidence: 'Opened with "Um, so" before the point.', score: 1 },
  },
  total_score: 83,
  passed: true,
  strongest_moment: 'Teenagers naturally stay up later and their brains just aren\'t ready to learn at seven in the morning.',
  weakest_function_id: 'recovery',
  feedback_pointer: 'Mock feedback — AI calls are disabled while testing. Try dropping the "um, so" and leading straight with your position.',
  next_focus: 'State your position in the first sentence, before explaining why.',
  delivery_metrics: {
    word_count: 28,
    duration_sec: 8.4,
    words_per_minute: 200,
    filler_word_count: 2,
    filler_words_found: ['um', 'so'],
    long_pause_count: 0,
    longest_pause_sec: 0,
    pause_details: [],
    time_to_first_content_word_sec: 2.5,
  },
  transcript: MOCK_TRANSCRIPT,
}

// Runs transcription and analysis, showing the waiting screen until the result
// is in. The result itself is rendered by <Feedback>, from the copy the parent
// keeps — so this unmounts once the analysis lands.
function AiFeedback({ topic, side, audioBlob, previous, onResult }) {
  const [status, setStatus] = useState('transcribing')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!audioBlob) return
    let cancelled = false

    if (SKIP_AI) {
      ;(async () => {
        setStatus('analysing')
        await new Promise((r) => setTimeout(r, 300))
        if (cancelled) return
        onResult(MOCK_FEEDBACK)
        setStatus('done')
      })()
      return () => {
        cancelled = true
      }
    }

    // One request: the server transcribes and scores in the same call, so
    // nothing has to be handed between invocations through a store.
    ;(async () => {
      try {
        const form = new FormData()
        form.append('request_id', requestIdFor(audioBlob))
        if (previous?.attempt_id) form.append('previous_attempt_id', previous.attempt_id)
        form.append('topic', topic)
        form.append('side', side)
        form.append('previous_next_focus', previous?.next_focus || '')
        form.append('audio', audioBlob, 'speech.wav')

        const res = await fetch('/api/analyze', {
          method: 'POST',
          credentials: 'same-origin',
          body: form,
        })
        if (!res.ok) throw new Error('analysis failed')

        const json = await res.json()
        if (cancelled) return
        onResult(json)
        setStatus('done')
      } catch {
        if (!cancelled) setStatus('error')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [topic, side, audioBlob, onResult, attempt, previous])

  const retry = () => {
    setStatus('transcribing')
    setAttempt((n) => n + 1)
  }

  if (status === 'error') {
    return <AnalysisError onRetry={retry} />
  }

  return <Analysing topic={topic} side={side} />
}

export default AiFeedback
