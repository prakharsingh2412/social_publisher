import api from './client';
import { AUTH } from './urls';

export const authApi = {
  async register(payload) {
    const { data } = await api.post(AUTH.register, payload);
    return data;
  },
  async login({ username, password }) {
    const { data } = await api.post(AUTH.login, { username, password });
    return data; // { access, refresh }
  },
  async logout(refresh) {
    try { await api.post(AUTH.logout, { refresh }); } catch { /* ignore */ }
  },
  async me() {
    const { data } = await api.get(AUTH.me);
    return data;
  },
};