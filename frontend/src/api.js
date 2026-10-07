// Thin fetch wrapper. Every API error has the shape {error: {code, message, details}}.
export class ApiError extends Error {
  constructor(status, body) {
    const err = body?.error ?? {};
    super(err.message || `Request failed (${status})`);
    this.status = status;
    this.code = err.code;
    this.details = err.details ?? [];
    this.extra = err;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`/api${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError(0, { error: { code: "NETWORK", message: "Can't reach the server. Check that it is running." } });
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return body;
}

export const api = {
  leaderboard: (trendDays = 7) => request(`/leaderboard?trendDays=${trendDays}`),
  users: () => request("/users"),
  user: (id) => request(`/users/${id}`),
  dashboard: (id, days = 30) => request(`/users/${id}/dashboard?days=${days}`),
  register: (data) => request("/users", { method: "POST", body: JSON.stringify(data) }),
  logActivity: (data) => request("/activities", { method: "POST", body: JSON.stringify(data) }),
};

// crypto.randomUUID only exists on secure origins (https / localhost), so fall back
// when the app is opened from another device on the LAN via http://192.168.x.x.
export function requestId() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}
