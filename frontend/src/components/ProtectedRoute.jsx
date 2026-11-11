import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // While we're checking the JWT / fetching /auth/me/, show a loading state
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center gap-3 text-gray-500">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-200 border-t-brand-pink" />
        <span>Loading…</span>
      </div>
    );
  }

  // Not logged in → bounce to /login, remembering the intended destination
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Logged in → render the protected content
  return children;
}