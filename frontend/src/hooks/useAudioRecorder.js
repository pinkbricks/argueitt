import { useCallback, useRef, useState } from 'react'
import { toWavBlob } from '../utils/wav'

export function useAudioRecorder() {
  const [audioUrl, setAudioUrl] = useState(null)
  const [error, setError] = useState(null)
  const [audioBlob, setAudioBlob] = useState(null)
  const recorderRef = useRef(null)
  const chunksRef = useRef([])

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

      const recorder = new MediaRecorder(stream)
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
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

  return { audioUrl, audioBlob, error, start, stop }
}
