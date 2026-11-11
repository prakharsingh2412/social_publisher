import { NavLink, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation(); // <-- Add this

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // <-- Add this function to scroll to top if already on the home page -->
  const handleLogoClick = (e) => {
    if (location.pathname === '/') {
      e.preventDefault(); // Stop React Router from doing a hard reload
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const navLinkClass = ({ isActive }) =>
    `text-sm font-medium transition-colors hover:text-brand-pink ${
      isActive ? 'text-brand-pink' : 'text-gray-500'
    }`;

  return (
    <nav className="sticky top-0 z-40 border-b border-gray-200 bg-white/80 backdrop-blur-md px-6 py-4">
      <div className="mx-auto flex max-w-6xl items-center justify-between">
        <div className="flex items-center gap-8">
          
          {/* Added onClick={handleLogoClick} here */}
          <NavLink to="/" onClick={handleLogoClick} className="text-lg font-bold text-brand-dark">
            📣 Social Publisher
          </NavLink>
          
          <div className="hidden md:flex md:gap-6">
            {user ? (
              <>
                <NavLink to="/dashboard" className={navLinkClass}>Dashboard</NavLink>
                <NavLink to="/posts" className={navLinkClass}>Posts</NavLink>
                <NavLink to="/settings/connections" className={navLinkClass}>Connections</NavLink>
              </>
            ) : (
              <>
                <Link to="/#about" className="text-sm font-medium text-gray-500 transition-colors hover:text-brand-pink">About</Link>
                <Link to="/#contact" className="text-sm font-medium text-gray-500 transition-colors hover:text-brand-pink">Contact</Link>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {user ? (
            <>
              <span className="text-sm font-medium text-gray-500">{user?.username}</span>
              <button
                onClick={handleLogout}
                className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="text-sm font-medium text-gray-600 hover:text-brand-dark">Sign in</NavLink>
              <NavLink to="/register" className="rounded-lg bg-brand-pink px-4 py-2 text-sm font-semibold text-white hover:bg-brand-pink/90">
                Get Started
              </NavLink>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}