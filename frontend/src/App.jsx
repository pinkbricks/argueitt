import { useCallback, useEffect, useState } from 'react'
import Landing from './pages/Landing'
import Speak from './pages/Speak'
import ComingSoon from './pages/ComingSoon'
import SignIn from './pages/SignIn'

function getPath() {
  return window.location.pathname
}

function App() {
  const [path, setPath] = useState(getPath())

  useEffect(() => {
    const onPopState = () => setPath(getPath())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const navigate = useCallback((to) => {
    if (to === getPath()) return
    window.history.pushState({}, '', to)
    setPath(to)
    window.scrollTo(0, 0)
  }, [])

  if (path === '/speak') {
    return <Speak onNavigate={navigate} />
  }

  if (path === '/sign-in') {
    return <SignIn onNavigate={navigate} />
  }

  if (path === '/') {
    return <Landing onNavigate={navigate} />
  }

  return <ComingSoon path={path} onNavigate={navigate} />
}

export default App
