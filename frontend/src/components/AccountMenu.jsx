import { useEffect, useRef, useState } from 'react'
import { LogOut } from 'lucide-react'

function initialOf(user) {
  const source = user.name || user.email || '?'
  return source.trim().charAt(0).toUpperCase()
}

// Avatar with a small menu under it. Google serves profile images from a host
// that rejects requests carrying a referrer, hence referrerPolicy; if the
// image fails anyway, the initial stands in.
function AccountMenu({ user, onSignOut }) {
  const [open, setOpen] = useState(false)
  const [imageFailed, setImageFailed] = useState(false)
  const wrapRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined

    const onPointerDown = (event) => {
      if (!wrapRef.current?.contains(event.target)) setOpen(false)
    }
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const showImage = user.picture && !imageFailed

  return (
    <div className="account" ref={wrapRef}>
      <button
        type="button"
        className="account-avatar"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((isOpen) => !isOpen)}
      >
        <span className="sr-only">{user.name || user.email || 'Account'}</span>
        {showImage ? (
          <img
            src={user.picture}
            alt=""
            referrerPolicy="no-referrer"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <span className="account-initial" aria-hidden="true">
            {initialOf(user)}
          </span>
        )}
      </button>

      {open && (
        <div className="account-menu" role="menu">
          <div className="account-identity">
            {user.name && <span className="account-name">{user.name}</span>}
            {user.email && <span className="account-email">{user.email}</span>}
          </div>

          <button
            type="button"
            className="account-signout"
            role="menuitem"
            onClick={() => {
              setOpen(false)
              onSignOut()
            }}
          >
            <LogOut size={15} aria-hidden="true" />
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}

export default AccountMenu
