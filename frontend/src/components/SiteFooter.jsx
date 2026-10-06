import SocialLinks from './SocialLinks'
import './SiteChrome.css'

function SiteFooter() {
  return (
    <footer className="landing-footer">
      <div className="footer-inner">
        <p className="footer-logo">Argueitt</p>
        <SocialLinks />
      </div>
    </footer>
  )
}

export default SiteFooter
