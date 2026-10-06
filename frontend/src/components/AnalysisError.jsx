import { ArrowRight } from 'lucide-react'
import TipCard from './TipCard'
import './AnalysisError.css'

// The landing page's blob, pulling a face. Same path and gradient stops as
// public/animated-orange-liquid-blob.svg, inlined so the face can sit on top
// of it and share its coordinate space. The mouth is a wave rather than a
// frown — the copy says "Hmm…", not "disaster".
function SadBlob() {
  return (
    <svg className="sad-blob" viewBox="0 0 180 180" aria-hidden="true">
      <defs>
        <radialGradient id="sadBlobGradient" cx="34%" cy="28%" r="75%">
          <stop offset="0%" stopColor="#FF8A5C" />
          <stop offset="48%" stopColor="#FF511A" />
          <stop offset="100%" stopColor="#A82E0C" />
        </radialGradient>
      </defs>

      <path
        className="sad-blob-body"
        d="M90 15 C118 15, 150 28, 158 60 C166 90, 158 122, 132 140 C106 158, 68 160, 42 140 C16 120, 12 84, 26 56 C40 28, 62 15, 90 15 Z"
      />

      <g className="sad-blob-face">
        <path
          className="sad-blob-eye sad-blob-eye-left"
          d="M64 67 Q71 64 77 68 Q80 79 78 90 Q71 93 65 90 Q62 79 64 67 Z"
        />
        <path
          className="sad-blob-eye sad-blob-eye-right"
          d="M105 66 Q112 64 118 69 Q120 80 117 91 Q110 94 104 90 Q103 78 105 66 Z"
        />
        <path
          className="sad-blob-mouth"
          d="M68 113 Q80 110 91 112 Q103 114 114 111 Q115 115 114 118 Q103 121 91 119 Q80 117 68 120 Q67 116 68 113 Z"
        />
      </g>

    </svg>
  )
}

function AnalysisError({ onRetry }) {
  return (
    <div className="analysis-error">
      <section className="error-main">
        <SadBlob />

        <h1 className="error-heading">Hmm… something went wrong.</h1>

        <p className="error-sub">
          We couldn&apos;t analyse your speech this time. But don&apos;t worry — it happens.
          You can try again or check out these quick tips to improve.
        </p>

        <button type="button" className="error-retry" onClick={onRetry}>
          Try again
          <ArrowRight size={18} aria-hidden="true" />
        </button>
      </section>

      <TipCard eyebrow="Quick tips" />
    </div>
  )
}

export default AnalysisError
