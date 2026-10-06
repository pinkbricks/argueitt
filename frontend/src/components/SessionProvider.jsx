import { useCallback, useEffect, useMemo, useState } from 'react'
import { SessionContext } from '../hooks/SessionContext'

// Asks the backend once who is signed in, and holds the answer for the whole
// app. A failed request means signed out rather than broken — practising never
// required an account, so a backend that is down shouldn't block the app.
function SessionProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false

    fetch('/api/auth/me', { credentials: 'same-origin' })
      .then((res) => (res.ok ? res.json() : { user: null }))
      .catch(() => ({ user: null }))
      .then((body) => {
        if (cancelled) return
        setUser(body.user ?? null)
        setStatus('ready')
      })

    return () => {
      cancelled = true
    }
  }, [])

  // The sign-in endpoint already returns the user, so there is no need to go
  // back and ask again.
  const signIn = useCallback((nextUser) => {
    setUser(nextUser)
    setStatus('ready')
  }, [])

  const signOut = useCallback(async () => {
    await fetch('/api/auth/sign-out', {
      method: 'POST',
      credentials: 'same-origin',
    }).catch(() => {})
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, status, signIn, signOut }),
    [user, status, signIn, signOut],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export default SessionProvider
