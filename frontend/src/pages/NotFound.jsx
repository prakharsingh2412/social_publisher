import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-gray p-6">
      <div className="w-full max-w-sm space-y-4 rounded-2xl border border-gray-100 bg-white p-8 text-center shadow-lg">
        <h1 className="text-4xl font-bold text-brand-pink">404</h1>
        <p className="text-gray-500">Page not found.</p>
        <Link to="/dashboard" className="inline-block rounded-lg bg-brand-pink px-6 py-2.5 text-sm font-semibold text-white hover:bg-brand-pink/90">
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}