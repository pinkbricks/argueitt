import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import './Landing.css'

// Positioned as percentages of the blob's square wrapper, eyeballed against
// the reference composition rather than laid out on a grid.
const FILLER_WORDS = [
  { text: '“Uhh…”', top: '4%', left: '-2%', scale: 1, drift: 'a', delay: '0s' },
  { text: '“y’know…”', top: '-7%', left: '24%', scale: 1.05, drift: 'b', delay: '0.9s' },
  { text: '“basically…”', top: '-3%', left: '87%', scale: 1.5, drift: 'c', delay: '1.6s' },
  { text: '“…literally”', top: '25%', left: '96%', scale: 1.05, drift: 'a', delay: '0.4s' },
  { text: '“I mean…”', top: '44%', left: '103%', scale: 0.8, drift: 'b', delay: '2s' },
  { text: '“just…”', top: '80%', left: '89%', scale: 1.15, drift: 'c', delay: '1.1s' },
  { text: '“so um…”', top: '103%', left: '67%', scale: 1.4, drift: 'a', delay: '0.6s' },
  { text: '“like”', top: '92%', left: '10%', scale: 1.05, drift: 'b', delay: '1.4s' },
]

function fillerStyle({ top, left, scale, delay }) {
  return {
    top,
    left,
    fontSize: `clamp(${(0.85 * scale).toFixed(2)}rem, ${(2.1 * scale).toFixed(2)}vw, ${(1.7 * scale).toFixed(2)}rem)`,
    animationDelay: delay,
  }
}

function fillerRotate(index) {
  return (index % 2 === 0 ? -1 : 1) * (3 + (index % 3) * 1.5)
}

function Landing({ onNavigate }) {
  const goSpeak = (event) => {
    event.preventDefault()
    onNavigate('/speak')
  }

  return (
    <div className="landing">
      <SiteHeader onNavigate={onNavigate} />

      <section className="hero">
        <div className="hero-copy">
          <h1 className="hero-headline">
            Become the most <br className="hero-break" />
            articulate person in the <br className="hero-break" />
            room
          </h1>
          <p className="hero-subhead">
            Speak on the spot and get an analysis
            <br />
            of how well you did.
          </p>
          <a href="/speak" className="btn-cta" onClick={goSpeak}>
            Start speaking
          </a>
        </div>

        <div className="hero-visual" aria-hidden="true">
          <div className="hero-blob-wrap">
            <img
              className="hero-blob"
              src="/animated-orange-liquid-blob.svg"
              alt=""
              width={600}
              height={600}
            />
            {FILLER_WORDS.map((word, index) => (
              <span key={word.text} className="filler-word" style={fillerStyle(word)}>
                <span
                  className="filler-word-rotate"
                  style={{ transform: `rotate(${fillerRotate(index)}deg)` }}
                >
                  <span className={`filler-word-inner drift-${word.drift}`}>{word.text}</span>
                </span>
              </span>
            ))}
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  )
}

export default Landing
