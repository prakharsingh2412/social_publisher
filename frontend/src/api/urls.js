const BASE = import.meta.env.VITE_API_BASE_URL || '';
const PREFIX = import.meta.env.VITE_API_PREFIX || '/api/v1';
const OAUTH_PREFIX = import.meta.env.VITE_OAUTH_PREFIX || '/oauth';

export const AUTH = {
  register: `${BASE}${PREFIX}/auth/register/`,
  login:    `${BASE}${PREFIX}/auth/login/`,
  refresh:  `${BASE}${PREFIX}/auth/refresh/`,
  logout:   `${BASE}${PREFIX}/auth/logout/`,
  me:       `${BASE}${PREFIX}/auth/me/`,
};

export const POSTS = {
  list:       `${BASE}${PREFIX}/posts/`,
  detail:     (id) => `${BASE}${PREFIX}/posts/${id}/`,
  publishNow: (id) => `${BASE}${PREFIX}/posts/${id}/publish-now/`,
};

export const PLATFORMS = {
  list:   `${BASE}${PREFIX}/platforms/`,
  detail: (id) => `${BASE}${PREFIX}/platforms/${id}/`,
};

export const OAUTH = {
  login: (platform) => `${BASE}${OAUTH_PREFIX}/${platform}/login/`,
};

export const SUPPORTED_PLATFORMS = ['facebook', 'instagram', 'twitter', 'youtube'];