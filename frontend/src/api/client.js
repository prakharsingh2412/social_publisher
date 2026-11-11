import axios from 'axios';
import { AUTH } from './urls';

const api = axios.create({ headers: { 'Content-Type': 'application/json' } });

// Attach JWT access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401 (single-flight queue)
let isRefreshing = false;
let queue = [];

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    const isAuthCall =
      original?.url?.includes('/auth/login/') ||
      original?.url?.includes('/auth/register/') ||
      original?.url?.includes('/auth/refresh/');

    if (err.response?.status === 401 && !original._retry && !isAuthCall) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          queue.push({ resolve, reject });
        }).then((token) => {
          original.headers.Authorization = `Bearer ${token}`;
          return api(original);
        });
      }

      original._retry = true;
      isRefreshing = true;
      try {
        const refresh = localStorage.getItem('refresh');
        if (!refresh) throw new Error('No refresh token');
        const { data } = await axios.post(AUTH.refresh, { refresh });
        localStorage.setItem('access', data.access);
        queue.forEach((p) => p.resolve(data.access));
        queue = [];
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch (e) {
        queue.forEach((p) => p.reject(e));
        queue = [];
        localStorage.removeItem('access');
        localStorage.removeItem('refresh');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(e);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(err);
  }
);

export default api;