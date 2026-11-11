import api from './client';
import { POSTS } from './urls';

export const postsApi = {
  async list({ page = 1, status = '', search = '' } = {}) {
    const params = { page };
    if (status) params.status = status;
    if (search) params.search = search;
    const { data } = await api.get(POSTS.list, { params });
    // Normalize paginated vs bare array responses
    return Array.isArray(data) ? { count: data.length, results: data } : data;
  },
  async create(payload) {
    const { data } = await api.post(POSTS.list, payload);
    return data;
  },
  async get(id) {
    const { data } = await api.get(POSTS.detail(id));
    return data;
  },
  async remove(id) {
    await api.delete(POSTS.detail(id));
  },
  async publishNow(id) {
    const { data } = await api.post(POSTS.publishNow(id));
    return data;
  },
};