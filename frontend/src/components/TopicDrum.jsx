import { useEffect, useRef, useState } from 'react'
import { motion, useMotionValue, useTransform, animate, useReducedMotion, MotionConfig } from 'motion/react'
import { ChevronUp, ChevronDown, AudioLines, Clock } from 'lucide-react'
import { topics as TOPICS } from '../data/topics'
import './TopicDrum.css'

const SPIN_MIN_SLOTS = 16
const SPIN_MAX_SLOTS = 26
const NAV_DURATION = 0.45
const SPIN_DURATION = 3.6
// Three-phase spin (spin up -> hold near top speed -> decelerate into the
// landing slot) instead of one easing curve — a single ease-out front-loads
// almost all the travel into the first fraction of the duration, so the
// "several topics passing through" phase reads as barely there.
const SPIN_TIMES = [0, 0.22, 0.62, 1]
const SPIN_DISTANCE_SHARE = [0, 0.18, 0.72, 1]
const SPIN_EASE = ['easeIn', 'linear', 'easeOut']
const RENDER_BUFFER = 3

function shuffle(items) {
  const a = [...items]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

// One card in the drum. `position` is the shared, continuously-animating
// slot position; `slot` is this card's fixed place in the reel. Deriving
// every visual property from `slot - position` is what makes the whole
// drum move as one physical strip instead of independently-tweened cards.
function DrumCard({ text, side, slot, position, cardHeight, isCenter, onSelect }) {
  const distance = useTransform(position, (p) => slot - p)
  const y = useTransform(distance, (d) => d * cardHeight * 0.78)
  const rotateX = useTransform(distance, (d) => clamp(d * 22, -42, 42))
  const scale = useTransform(distance, (d) => clamp(1 - Math.abs(d) * 0.22, 0.62, 1))
  const opacity = useTransform(distance, (d) => clamp(1 - Math.abs(d) * 0.48, 0, 1))
  const blur = useTransform(distance, (d) => `blur(${clamp(Math.abs(d) * 1.6, 0, 4)}px)`)
  const brightness = useTransform(distance, (d) => `brightness(${clamp(1 - Math.abs(d) * 0.1, 0.78, 1)})`)
  const filter = useTransform([blur, brightness], ([b, br]) => `${b} ${br}`)
  const ringOpacity = useTransform(distance, (d) => clamp(1 - Math.abs(d) * 2.2, 0, 1))

  return (
    <motion.button
      type="button"
      className={`drum-card${isCenter ? ' is-center' : ''}`}
      style={{
        height: cardHeight,
        marginTop: -cardHeight / 2,
        y,
        rotateX,
        scale,
        opacity,
        filter,
      }}
      onClick={onSelect}
      tabIndex={isCenter ? 0 : -1}
      aria-hidden={!isCenter}
      aria-current={isCenter ? 'true' : undefined}
    >
      <motion.span className="drum-card-ring" style={{ opacity: ringOpacity }} aria-hidden="true" />
      <span className="drum-card-inner">
        <p className="drum-card-text">{text}</p>
        <span className={`drum-card-pill drum-card-pill-${side}`}>
          {side === 'for' ? 'For' : 'Against'}
        </span>
      </span>
    </motion.button>
  )
}

function TopicDrum({ onConfirm, duration = 60 }) {
  const prefersReducedMotion = useReducedMotion()
  const [order] = useState(() => shuffle(TOPICS.map((_, i) => i)))
  // Which side each reel position argues — decided once per position so a
  // card's "For"/"Against" pill never flickers to something else later, and
  // so the side landed on visually is exactly the side carried into the
  // next screen (see onConfirm below).
  const [sides] = useState(() => order.map(() => (Math.random() < 0.5 ? 'for' : 'against')))
  const total = order.length
  const wrap = (slot) => ((slot % total) + total) % total
  const reelAt = (slot) => order[wrap(slot)]
  const sideAt = (slot) => sides[wrap(slot)]

  const [settledSlot, setSettledSlot] = useState(0)
  const [renderRange, setRenderRange] = useState({ start: -RENDER_BUFFER, end: RENDER_BUFFER })
  const [isSpinning, setIsSpinning] = useState(false)
  const position = useMotionValue(0)

  const viewportRef = useRef(null)
  const [cardHeight, setCardHeight] = useState(140)

  useEffect(() => {
    const el = viewportRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      setCardHeight(clamp(entry.contentRect.height * 0.42, 100, 160))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const goTo = (target, { isSpin = false } = {}) => {
    if (isSpinning || target === settledSlot) return
    const lo = Math.min(settledSlot, target) - RENDER_BUFFER
    const hi = Math.max(settledSlot, target) + RENDER_BUFFER
    setRenderRange({ start: lo, end: hi })
    setIsSpinning(true)

    const onComplete = () => {
      setSettledSlot(target)
      setRenderRange({ start: target - RENDER_BUFFER, end: target + RENDER_BUFFER })
      setIsSpinning(false)
      if (isSpin) onConfirm(reelAt(target), sideAt(target))
    }

    if (prefersReducedMotion) {
      animate(position, target, { duration: 0.3, ease: 'easeOut', onComplete })
      return
    }

    if (!isSpin) {
      animate(position, target, { duration: NAV_DURATION, ease: 'easeOut', onComplete })
      return
    }

    const start = settledSlot
    const span = target - start
    const keyframes = SPIN_DISTANCE_SHARE.map((share) => start + span * share)
    animate(position, keyframes, {
      duration: SPIN_DURATION,
      times: SPIN_TIMES,
      ease: SPIN_EASE,
      onComplete,
    })
  }

  const spin = () => {
    const distance = SPIN_MIN_SLOTS + Math.floor(Math.random() * (SPIN_MAX_SLOTS - SPIN_MIN_SLOTS + 1))
    goTo(settledSlot + distance, { isSpin: true })
  }

  const slots = []
  for (let s = renderRange.start; s <= renderRange.end; s++) slots.push(s)

  return (
    <MotionConfig reducedMotion="user">
      <section className="topic-drum-page">
        <p className="topic-drum-eyebrow">Speak &middot; Think &middot; Improve</p>
        <h1 className="topic-drum-heading">Spin to get a random topic.</h1>
        <p className="topic-drum-subhead">
          You don’t choose the side. We do. You’ll have {duration} seconds to make your case.
        </p>

        <div className="topic-drum" role="group" aria-label="Speaking topic carousel" aria-live="polite">
          <button
            type="button"
            className="drum-arrow"
            aria-label="Previous topic"
            onClick={() => goTo(settledSlot - 1)}
            disabled={isSpinning}
          >
            <ChevronUp aria-hidden="true" size={20} />
          </button>

          <div className="topic-drum-viewport" ref={viewportRef}>
            <span className="drum-end drum-end-top" aria-hidden="true" />
            {slots.map((slot) => (
              <DrumCard
                key={slot}
                slot={slot}
                text={TOPICS[reelAt(slot)]}
                side={sideAt(slot)}
                position={position}
                cardHeight={cardHeight}
                isCenter={slot === settledSlot}
                onSelect={() => goTo(slot)}
              />
            ))}
            <span className="drum-end drum-end-bottom" aria-hidden="true" />
          </div>

          <button
            type="button"
            className="drum-arrow"
            aria-label="Next topic"
            onClick={() => goTo(settledSlot + 1)}
            disabled={isSpinning}
          >
            <ChevronDown aria-hidden="true" size={20} />
          </button>
        </div>

        <motion.button
          type="button"
          className="drum-cta"
          onClick={spin}
          disabled={isSpinning}
          whileHover={isSpinning ? undefined : { scale: 1.03 }}
          whileTap={isSpinning ? undefined : { scale: 0.97 }}
        >
          <AudioLines aria-hidden="true" size={18} />
          <span>Spin to speak</span>
          <span className="drum-cta-meta">
            <span className="drum-cta-divider" aria-hidden="true" />
            <Clock aria-hidden="true" size={16} />
            <span>{duration} sec</span>
          </span>
        </motion.button>
      </section>
    </MotionConfig>
  )
}

export default TopicDrum
