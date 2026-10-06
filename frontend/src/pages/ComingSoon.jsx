function ComingSoon({ path, onNavigate }) {
  return (
    <main className="coming-soon">
      <p className="coming-soon-eyebrow">Coming soon</p>
      <h1>This page isn't ready yet.</h1>
      <p className="coming-soon-path">{path}</p>
      <a
        className="coming-soon-link"
        href="/"
        onClick={(e) => {
          e.preventDefault()
          onNavigate('/')
        }}
      >
        Back to home
      </a>
    </main>
  )
}

export default ComingSoon
