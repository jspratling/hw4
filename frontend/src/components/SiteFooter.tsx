import { Link } from 'react-router-dom'
import Crest from './Crest'

/** Problem 10: footer on every page, with the store's story and the spirit line. */
export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <Crest size={44} />
          <div>
            <p className="footer-name">Campus Customs</p>
            <p className="footer-address">57 Broadway, New Haven, Connecticut</p>
          </div>
        </div>
        <p className="footer-story">
          A campus shop for students, alumni and the families who cheer them on, from first-year
          move-in to Commencement and every game day in between.
        </p>
        <nav className="footer-links" aria-label="Footer">
          <Link to="/products">Shop all</Link>
          <Link to="/products?style=Formal">Formal styles</Link>
          <Link to="/products?season=now">In season</Link>
          <Link to="/about">About us</Link>
        </nav>
      </div>
      <p className="footer-spirit">Go Yale! Beat Harvard!</p>
    </footer>
  )
}
