import { useRef, useState } from 'react'
import { Pause, Play, Volume2, VolumeX } from 'lucide-react'
import './AudioPlayer.css'

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

// Native controls can't be styled to match the card, so the <audio> element is
// kept headless and driven from here. Callers key this by `src` so a new
// recording starts from a clean player rather than inheriting the old state.
function AudioPlayer({ src }) {
  const audioRef = useRef(null)
  const [playing, setPlaying] = useState(false)
  const [muted, setMuted] = useState(false)
  const [current, setCurrent] = useState(0)
  const [duration, setDuration] = useState(0)

  const onLoaded = () => {
    const value = audioRef.current?.duration
    // Blobs from MediaRecorder often report Infinity until they are seeked.
    setDuration(Number.isFinite(value) ? value : 0)
  }

  const toggle = () => {
    const audio = audioRef.current
    if (!audio) return
    if (audio.paused) {
      audio.play()
      setPlaying(true)
    } else {
      audio.pause()
      setPlaying(false)
    }
  }

  const seek = (event) => {
    const audio = audioRef.current
    if (!audio) return
    const value = Number(event.target.value)
    audio.currentTime = value
    setCurrent(value)
  }

  const toggleMute = () => {
    const audio = audioRef.current
    if (!audio) return
    audio.muted = !audio.muted
    setMuted(audio.muted)
  }

  const progress = duration > 0 ? (current / duration) * 100 : 0

  return (
    <div className="player">
      <audio
        ref={audioRef}
        src={src}
        preload="metadata"
        onLoadedMetadata={onLoaded}
        onDurationChange={onLoaded}
        onTimeUpdate={() => setCurrent(audioRef.current?.currentTime || 0)}
        onEnded={() => setPlaying(false)}
      />

      <button type="button" className="player-play" onClick={toggle}>
        <span className="sr-only">{playing ? 'Pause recording' : 'Play recording'}</span>
        {playing ? <Pause size={16} fill="currentColor" /> : <Play size={16} fill="currentColor" />}
      </button>

      <input
        type="range"
        className="player-scrub"
        min={0}
        max={duration || 0}
        step={0.01}
        value={current}
        onChange={seek}
        aria-label="Seek"
        style={{ '--player-progress': `${progress}%` }}
      />

      <span className="player-time">
        {formatTime(current)} / {formatTime(duration)}
      </span>

      <button type="button" className="player-mute" onClick={toggleMute}>
        <span className="sr-only">{muted ? 'Unmute' : 'Mute'}</span>
        {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
      </button>
    </div>
  )
}

export default AudioPlayer
