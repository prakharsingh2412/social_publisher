import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export default function Login() {
  const { login } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  
  // State to toggle password visibility
  const [showPassword, setShowPassword] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(''); setBusy(true);
    try {
      await login(form.username, form.password);
      push('Welcome back!', 'success');
      navigate(location.state?.from?.pathname || '/dashboard', { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-brand-gray font-sans">
      <Navbar />
      
      <main className="flex flex-1 items-center justify-center bg-gradient-to-br from-brand-gray via-white to-pink-50 p-6">
        <form onSubmit={onSubmit} className="w-full max-w-md space-y-4 rounded-2xl border border-gray-100 bg-white p-8 shadow-xl">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-brand-dark">Sign in</h1>
            <p className="mt-1 text-sm text-gray-500">Welcome back to Social Publisher.</p>
          </div>

          {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Username</label>
            <input 
              name="username" 
              value={form.username} 
              onChange={onChange} 
              autoComplete="username" 
              required 
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-brand-pink focus:outline-none focus:ring-2 focus:ring-brand-pink/20"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Password</label>
            <div className="relative">
              <input 
                name="password" 
                type={showPassword ? 'text' : 'password'} 
                value={form.password} 
                onChange={onChange} 
                autoComplete="current-password" 
                required 
                className="w-full rounded-lg border border-gray-300 pl-4 pr-10 py-2.5 text-sm focus:border-brand-pink focus:outline-none focus:ring-2 focus:ring-brand-pink/20"
              />
              {/* Eye Toggle Button */}
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 focus:outline-none"
              >
                {showPassword ? (
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          <button 
            disabled={busy}
            className="w-full rounded-lg bg-brand-pink px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-pink/90 disabled:opacity-50"
          >
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
          
          <p className="text-center text-sm text-gray-500">
            No account? <Link to="/register" className="font-semibold text-brand-pink hover:underline">Create one</Link>
          </p>
        </form>
      </main>

      <Footer />
    </div>
  );
}