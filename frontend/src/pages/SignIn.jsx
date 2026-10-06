import { useCallback, useEffect, useRef, useState } from 'react'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import { useSession } from '../hooks/useSession'
import './SignIn.css'

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID
const GSI_SRC = 'https://accounts.google.com/gsi/client'

// Google Identity Services renders its own button. It can't be restyled beyond
// the options passed to renderButton — their branding terms require their mark,
// wording and colours — and since FedCM became mandatory in August 2025,
// letting their library own the button is also what keeps the flow working.
function useGoogleScript() {
  const [state, setState] = useState(() =>
    window.google?.accounts?.id ? 'ready' : 'loading',
  )

  useEffect(() => {
    if (window.google?.accounts?.id) return undefined

    const existing = document.querySelector(`script[src="${GSI_SRC}"]`)
    const script = existing || document.createElement('script')
    const onLoad = () => setState('ready')
    const onError = () => setState('failed')

    script.addEventListener('load', onLoad)
    script.addEventListener('error', onError)

    if (!existing) {
      script.src = GSI_SRC
      script.async = true
      document.head.appendChild(script)
    }

    return () => {
      script.removeEventListener('load', onLoad)
      script.removeEventListener('error', onError)
    }
  }, [])

  return state
}

// Sits on the card's top-right corner and runs over the edge — the drips are
// drawn before the blob so the joins disappear underneath it.
function MeltingBlob() {
  return (
    <svg className="signin-blob" viewBox="0 0 170 230" aria-hidden="true">
      <defs>
        <linearGradient id="meltGradient" x1="0" y1="0" x2="0.3" y2="1">
          <stop offset="0%" stopColor="#FF8A5C" />
          <stop offset="55%" stopColor="#FF511A" />
          <stop offset="100%" stopColor="#D13A0C" />
        </linearGradient>
      </defs>

      <g className="signin-drips">
        <path className="signin-drip signin-drip-a" d="M36 70 h20 v62 a10 10 0 0 1 -20 0 Z" />
        <path className="signin-drip signin-drip-b" d="M74 76 h24 v104 a12 12 0 0 1 -24 0 Z" />
        <path className="signin-drip signin-drip-c" d="M116 68 h17 v44 a8.5 8.5 0 0 1 -17 0 Z" />
      </g>

      <path
        className="signin-blob-body"
        d="M86 4 C116 4, 150 18, 157 50 C164 80, 152 104, 124 112 C96 120, 60 118, 36 104 C12 90, 6 60, 20 36 C34 12, 56 4, 86 4 Z"
      />
    </svg>
  )
}

function SignIn({ onNavigate }) {
  const buttonRef = useRef(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const scriptState = useGoogleScript()
  const { user, status, signIn } = useSession()

  // Nobody who is already signed in has any business on this page.
  useEffect(() => {
    if (status === 'ready' && user) onNavigate('/')
  }, [status, user, onNavigate])

  // Google hands back a signed JWT; the backend is what decides whether to
  // trust it, so nothing here reads the token's contents.
  //
  // Failures are reported by what actually went wrong. A 401 is Google's
  // answer and worth showing the user; anything else means the request never
  // reached a working endpoint — most often the backend not running, or
  // running from before these routes existed — and saying "try again" for
  // that just sends people round the same loop.
  const onCredential = useCallback(
    async ({ credential }) => {
      setBusy(true)
      setError('')
      try {
        const res = await fetch('/api/auth/google', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ credential }),
        })

        if (res.ok) {
          signIn(await res.json())
          onNavigate('/speak')
          return
        }

        const detail = await res.json().then((b) => b?.detail).catch(() => null)
        setBusy(false)

        if (res.status === 401) {
          setError(detail || 'Google couldn’t confirm that account. Please try again.')
        } else if (res.status === 404) {
          setError('The sign-in endpoint isn’t there. Restart the backend so it picks up the auth routes.')
        } else {
          setError(`Sign-in failed (${res.status}). ${detail || 'Check the backend logs.'}`)
        }
      } catch {
        setBusy(false)
        setError('Couldn’t reach the server. Is the backend running on port 8000?')
      }
    },
    [onNavigate, signIn],
  )

  useEffect(() => {
    if (scriptState !== 'ready' || !CLIENT_ID || !buttonRef.current) return

    window.google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: onCredential,
    })

    window.google.accounts.id.renderButton(buttonRef.current, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      shape: 'pill',
      text: 'signin_with',
      logo_alignment: 'left',
      width: 300,
    })
  }, [scriptState, onCredential])

  if (status !== 'ready' || user) {
    return (
      <main className="app">
        <SiteHeader onNavigate={onNavigate} />
        <div className="signin-main" />
        <SiteFooter />
      </main>
    )
  }

  return (
    <main className="app">
      <SiteHeader onNavigate={onNavigate} />

      <div className="signin-main">
        <section className="signin-card">
          <MeltingBlob />

          <p className="signin-eyebrow">Welcome back</p>
          <h1 className="signin-heading">Sign in to Argueitt.</h1>
          <p className="signin-sub">
            Keep your attempts, track your progress and pick up where you left off.
          </p>

          <div className="signin-button-slot">
            <div ref={buttonRef} />

            {!CLIENT_ID && (
              <p className="signin-notice" role="status">
                Google sign-in isn’t configured. Set VITE_GOOGLE_CLIENT_ID in
                frontend/.env.local and restart the dev server.
              </p>
            )}

            {CLIENT_ID && scriptState === 'failed' && (
              <p className="signin-notice" role="status">
                Couldn’t reach Google just now. Check your connection and reload.
              </p>
            )}

            {busy && <p className="signin-progress">Signing you in…</p>}

            {error && (
              <p className="signin-notice" role="alert">
                {error}
              </p>
            )}
          </div>

          <p className="signin-terms">
            By continuing you agree to Argueitt&apos;s terms and privacy policy.
          </p>

          <a
            className="signin-skip"
            href="/speak"
            onClick={(event) => {
              event.preventDefault()
              onNavigate('/speak')
            }}
          >
            Keep practising without an account
          </a>
        </section>
      </div>

      <SiteFooter />
    </main>
  )
}

export default SignIn
