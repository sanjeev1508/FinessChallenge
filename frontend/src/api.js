// Thin fetch wrapper. Every API error has the shape {error: {code, message, details}}.
const TOKEN_KEY = "fitness-challenge:accessToken";

function readAccessToken() {
  try { return globalThis.localStorage?.getItem(TOKEN_KEY) ?? null; } catch { return null; }
}

let accessToken = readAccessToken();

if (typeof window !== "undefined") {
  window.addEventListener("storage", (event) => {
    if (event.key === TOKEN_KEY) accessToken = event.newValue;
  });
}

export function setAccessToken(token) {
  accessToken = token;
  try {
    if (token) globalThis.localStorage?.setItem(TOKEN_KEY, token);
    else globalThis.localStorage?.removeItem(TOKEN_KEY);
  } catch {
    // Keep the in-memory token for this page when browser storage is unavailable.
  }
}

export function hasAccessToken() {
  return Boolean(accessToken);
}

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
  const { headers: requestHeaders, ...requestOptions } = options;
  try {
    res = await fetch(`/api${path}`, {
      ...requestOptions,
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...requestHeaders,
      },
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(0, { error: { code: "NETWORK", message: "Can't reach the server. Check that it is running." } });
  }
  let body;
  try {
    body = await res.json();
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(res.status, { error: { code: "INVALID_RESPONSE", message: "The server returned an invalid response. Please try again." } });
  }
  if (!res.ok) {
    if (res.status === 401) {
      setAccessToken(null);
      if (typeof globalThis.dispatchEvent === "function" && typeof Event !== "undefined") {
        globalThis.dispatchEvent(new Event("fitness-auth-expired"));
      }
    }
    throw new ApiError(res.status, body);
  }
  return body;
}

export const api = {
  leaderboard: (trendDays = 7, options = {}) => request(`/leaderboard?trendDays=${trendDays}`, options),
  users: (options = {}) => request("/users", options),
  user: (id, options = {}) => request(`/users/${id}`, options),
  dashboard: (id, days = 30, options = {}) => request(`/users/${id}/dashboard?days=${days}`, options),
  register: (data) => request("/users", { method: "POST", body: JSON.stringify(data) }),
  login: (data) => request("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  me: (options = {}) => request("/auth/me", options),
  logActivity: (data) => request("/activities", { method: "POST", body: JSON.stringify(data) }),
};

// crypto.randomUUID only exists on secure origins (https / localhost), so fall back
// when the app is opened from another device on the LAN via http://192.168.x.x.
export function requestId() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}
