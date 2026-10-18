import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { useCart } from '../cart'
import Crest from './Crest'

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products', end: false },
  { to: '/about', label: 'About Us', end: true },
]

export default function NavBar() {
  const { user, logout } = useAuth()
  const { count } = useCart()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <header className="navbar">
      <nav className="navbar-inner" aria-label="Main">
        <Link to="/" className="brand" aria-label="Campus Customs home">
          <Crest size={30} />
          <span className="brand-text">
            <span className="brand-name">Campus Customs</span>
            <span className="brand-place">New Haven, Connecticut</span>
          </span>
        </Link>
        <ul className="nav-links">
          {LINKS.map((l) => (
            <li key={l.to}>
              <NavLink to={l.to} end={l.end}>
                {l.label}
              </NavLink>
            </li>
          ))}
        </ul>
        <ul className="nav-account">
          <li>
            <NavLink to="/cart" className="nav-cart" aria-label={`Cart, ${count} item${count === 1 ? '' : 's'}`}>
              Cart{count > 0 && <span className="cart-badge">{count}</span>}
            </NavLink>
          </li>
          {user ? (
            <>
              <li className="nav-greeting">Hi, {user.first_name}</li>
              <li>
                <button type="button" className="nav-logout" onClick={handleLogout}>
                  Log out
                </button>
              </li>
            </>
          ) : (
            <>
              <li>
                <NavLink to="/login">Log in</NavLink>
              </li>
              <li>
                <NavLink to="/register" className="nav-cta">
                  Create account
                </NavLink>
              </li>
            </>
          )}
        </ul>
      </nav>
    </header>
  )
}
