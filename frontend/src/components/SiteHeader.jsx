import { useState } from 'react'
import AccountMenu from './AccountMenu'
import { useSession } from '../hooks/useSession'
import './SiteChrome.css'

const NAV_LINKS = [
  { label: 'Practice', to: '/speak' },
  { label: 'Progress', to: '/progress' },
]

function SiteHeader({ onNavigate }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const { user, status, signOut } = useSession()

  const go = (to) => (event) => {
    event.preventDefault()
    setMenuOpen(false)
    onNavigate(to)
  }

  return (
    <header className="landing-header">
      <a className="landing-logo" href="/" onClick={go('/')}>
        Argueitt
      </a>

      <div className="landing-header-right">
        <nav
          id="primary-nav"
          className={`landing-nav${menuOpen ? ' is-open' : ''}`}
          aria-label="Primary"
        >
          {NAV_LINKS.map(({ label, to }) => (
            <a key={to} href={to} onClick={go(to)}>
              {label}
            </a>
          ))}
          {!user && (
            <a href="/sign-in" className="btn-signin nav-signin" onClick={go('/sign-in')}>
              Sign In
            </a>
          )}
        </nav>

        {status === 'loading' ? (
          <span className="account-placeholder" aria-hidden="true" />
        ) : user ? (
          <AccountMenu user={user} onSignOut={signOut} />
        ) : (
          <a href="/sign-in" className="btn-signin desktop-signin" onClick={go('/sign-in')}>
            Sign In
          </a>
        )}

        <button
          type="button"
          className="menu-toggle"
          aria-expanded={menuOpen}
          aria-controls="primary-nav"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className="sr-only">{menuOpen ? 'Close menu' : 'Open menu'}</span>
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">
            {menuOpen ? (
              <path
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                d="M5 5l14 14M19 5L5 19"
              />
            ) : (
              <path
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                d="M4 7h16M4 12h16M4 17h16"
              />
            )}
          </svg>
        </button>
      </div>
    </header>
  )
}

export default SiteHeader
