export const todayISO = (now = new Date()) => now.toISOString().slice(0, 10);

export function formatDate(iso, options = {}) {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString(undefined, { ...options, timeZone: "UTC" });
}
