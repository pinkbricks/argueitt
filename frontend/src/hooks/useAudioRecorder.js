import { useCallback, useRef, useState } from 'react'
import { toWavBlob } from '../utils/wav'

export function useAudioRecorder() {
  const [audioUrl, setAudioUrl] = useState(null)
  const [error, setError] = useState(null)
  const [audioBlob, setAudioBlob] = useState(null)
  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  // Exposed as a ref (not state) so the live waveform can read frequency
  // data on every animation frame without forcing this hook to re-render.
  const analyserRef = useRef(null)
  const audioContextRef = useRef(null)

  const start = useCallback(async () => {
    setError(null)
    setAudioBlob(null)
    setAudioUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return null
    })
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      chunksRef.current = []

      try {
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext
        const audioContext = new AudioContextCtor()
        const source = audioContext.createMediaStreamSource(stream)
        const analyser = audioContext.createAnalyser()
        analyser.fftSize = 64
        source.connect(analyser)
        audioContextRef.current = audioContext
        analyserRef.current = analyser
      } catch {
        // Live waveform is a nice-to-have; recording still works without it.
        analyserRef.current = null
      }

      const recorder = new MediaRecorder(stream)
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        audioContextRef.current?.close()
        audioContextRef.current = null
        analyserRef.current = null
        const recordedBlob = new Blob(chunksRef.current, { type: recorder.mimeType })
        try {
          const wavBlob = await toWavBlob(recordedBlob)
          setAudioBlob(wavBlob)
          setAudioUrl(URL.createObjectURL(wavBlob))
        } catch {
          setAudioBlob(recordedBlob)
          setAudioUrl(URL.createObjectURL(recordedBlob))
        }
      }
      recorderRef.current = recorder
      recorder.start()
      return true
    } catch {
      setError('Microphone access is needed to record your argument.')
      return false
    }
  }, [])

  const stop = useCallback(() => {
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') recorder.stop()
  }, [])

  return { audioUrl, audioBlob, error, start, stop, analyserRef }
}
