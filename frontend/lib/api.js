const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

async function apiFetch(path) {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  health: () => apiFetch('/health'),
  activities: (userId, limit = 20) => apiFetch(`/auth/activities/${userId}?limit=${limit}`),
  fitness: (userId) => apiFetch(`/analysis/fitness/${userId}`),
  summary: (userId) => apiFetch(`/analysis/summary/${userId}`),
  balance: (userId) => apiFetch(`/analysis/balance/${userId}`),
  hrZones: (userId, activityId) => apiFetch(`/analysis/hr-zones/${userId}/${activityId}`),
  sync: (userId) => apiFetch(`/auth/sync/${userId}`),
  calculateTss: (userId) => apiFetch(`/analysis/calculate-tss/${userId}`),
};
