import api from './client';
import { PLATFORMS, OAUTH } from './urls';

export const platformsApi = {
  async list() {
    const { data } = await api.get(PLATFORMS.list);
    return Array.isArray(data) ? data : data.results || [];
  },
  async remove(id) {
    await api.delete(PLATFORMS.detail(id));
  },
  async startOAuth(platform) {
    const { data } = await api.get(OAUTH.login(platform));
    return data; // { auth_url }
  },
};