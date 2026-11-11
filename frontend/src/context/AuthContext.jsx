import { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const token = localStorage.getItem('access');
      if (!token) { setLoading(false); return; }
      try {
        const me = await authApi.me();
        setUser(me);
      } catch {
        localStorage.removeItem('access');
        localStorage.removeItem('refresh');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = async (username, password) => {
    const { access, refresh } = await authApi.login({ username, password });
    localStorage.setItem('access', access);
    localStorage.setItem('refresh', refresh);
    const me = await authApi.me();
    setUser(me);
    return me;
  };

  const register = async (payload) => {
    await authApi.register(payload);
    return login(payload.username, payload.password);
  };

  const logout = async () => {
    const refresh = localStorage.getItem('refresh');
    if (refresh) await authApi.logout(refresh);
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);