import { useEffect, useState } from 'react'

const STEPS = ['3', '2', '1', 'Go!']

function Countdown({ onDone }) {
  const [step, setStep] = useState(0)

  useEffect(() => {
    const t = setTimeout(
      () => (step < STEPS.length - 1 ? setStep(step + 1) : onDone()),
      step === STEPS.length - 1 ? 700 : 1000,
    )
    return () => clearTimeout(t)
  }, [step, onDone])

  return (
    <div className="countdown">
      <span key={step} className="countdown-num">
        {STEPS[step]}
      </span>
    </div>
  )
}

export default Countdown
