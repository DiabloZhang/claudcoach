const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

function getToken() {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('token');
  }
  return null;
}

function setToken(token) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('token', token);
  }
}

function removeToken() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('token');
  }
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (res.status === 401) {
    removeToken();
    if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
      window.location.href = '/login';
    }
    throw new Error('登录已过期，请重新登录');
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `API error: ${res.status}`);
  }
  return res.json();
}

async function apiPost(path, body) {
  return apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

async function apiPut(path, body) {
  return apiFetch(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

async function apiDelete(path) {
  return apiFetch(path, { method: 'DELETE' });
}

export const authApi = {
  login: (email, password) => apiPost('/auth/login', { email, password }),
  register: (email, password, nickname) => apiPost('/auth/register', { email, password, nickname }),
  me: () => apiFetch('/auth/me'),
  updateProfile: (body) => apiPut('/auth/profile', body),
  changePassword: (oldPassword, newPassword) => apiPost('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
  status: () => apiFetch('/strava/status'),
  disconnectStrava: () => apiPost('/auth/strava/disconnect', {}),
  getDataSources: () => apiFetch('/auth/data-sources'),
  createDataSource: (body) => apiPost('/auth/data-sources', body),
  deleteDataSource: (id) => apiDelete(`/auth/data-sources/${id}`),
  getState: (key) => apiFetch(`/auth/state/${key}`),
  setState: (key, value) => apiPost(`/auth/state/${key}`, { value }),
};

export const api = {
  health: () => apiFetch('/health'),
  activities: (limit = 20) => apiFetch(`/strava/activities?limit=${limit}`),
  fitness: (days = 90) => apiFetch(`/analysis/fitness?days=${days}`),
  summary: () => apiFetch('/analysis/summary'),
  balance: (days = 28) => apiFetch(`/analysis/balance?days=${days}`),
  hrZones: (activityId) => apiFetch(`/analysis/hr-zones/${activityId}`),
  sync: () => apiFetch('/strava/sync'),
  syncFrom: (since) => apiFetch(`/strava/sync?since=${since}`),
  syncLogs: () => apiFetch('/strava/sync-logs'),
  backfill: () => apiFetch('/analysis/anomalies/backfill'),
  calculateTss: () => apiFetch('/analysis/calculate-tss'),
  coachOpen: () => apiFetch('/coach/open'),
  coachNew: () => apiPost('/coach/new', {}),
  coachMessage: (convId, content) => apiPost(`/coach/message/${convId}`, { content }),
  coachModelPreference: () => apiFetch('/coach/model-preference'),
  updateCoachModelPreference: (providerOrder) => apiPut('/coach/model-preference', { provider_order: providerOrder }),
  coachNotes: () => apiFetch('/coach/notes'),
  coachModelLogs: (convId) => apiFetch(`/coach/conversations/${convId}/model-logs`),
};

export { getToken, setToken, removeToken };
