import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import HandsomeDan from './HandsomeDan'
import SearchBar from './SearchBar'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, loading, logout } = useAuth()
  const { clearResults } = useChatResults()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    clearResults() // the next person on this browser shouldn't see this shopper's searches
    navigate('/')
  }

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="brand">
          <span className="brand-mark">Y</span>
          <span className="brand-text">
            Campus Customs
            <small>Yale Bulldog Blue · Est. 1975</small>
          </span>
        </Link>
        <SearchBar />
        <nav className="nav-links">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}>
              {l.label}
            </NavLink>
          ))}
          {!loading &&
            (user ? (
              <>
                <span className="nav-greeting">Hi, {user.first_name}</span>
                <button className="nav-button" onClick={handleLogout}>
                  Log Out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login">Log In</NavLink>
                {/* Handsome Dan peeks out under the one button we most want clicked */}
                <span className="cta-wrap">
                  <span className="cta-dan" aria-hidden="true">
                    <HandsomeDan variant="hang" size={56} />
                  </span>
                  <NavLink to="/create-account" className="nav-cta">
                    Create Account
                  </NavLink>
                </span>
              </>
            ))}
        </nav>
      </div>
    </header>
  )
}
