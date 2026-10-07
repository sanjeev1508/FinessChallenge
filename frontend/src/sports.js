// Display metadata only. Points shown in the form are a preview; the server is the
// source of truth and recomputes everything.
export const SPORTS = {
  running:  { label: "Running",  metric: "distance", unit: "km",    rate: 100, color: "#D9480F" },
  walking:  { label: "Walking",  metric: "distance", unit: "km",    rate: 50,  color: "#2A9D8F" },
  cycling:  { label: "Cycling",  metric: "distance", unit: "km",    rate: 25,  color: "#2450D6" },
  swimming: { label: "Swimming", metric: "duration", unit: "min",   rate: 15,  color: "#3FA7D6" },
  gym:      { label: "Gym",      metric: "duration", unit: "min",   rate: 5,   color: "#8E5BD9" },
  steps:    { label: "Steps",    metric: "count",    unit: "steps", rate: 1,   color: "#6C8E3B" },
};
export const SPORT_KEYS = Object.keys(SPORTS);

// Mirrors backend/app/scoring.py with integer maths (metres / seconds / steps).
export function previewPoints(sport, { km, minutes, seconds, steps }) {
  const s = SPORTS[sport];
  if (s.metric === "distance") {
    const value = Number(km);
    if (!Number.isFinite(value) || value <= 0 || value > 1000) return 0;
    const [whole, fraction = ""] = String(value).split(".");
    if (fraction.length > 3) return 0;
    const metres = Number(whole) * 1000 + Number(fraction.padEnd(3, "0"));
    return Math.floor((metres * s.rate) / 1000);
  }
  if (s.metric === "duration") {
    const m = Number(minutes || 0), sec = Number(seconds || 0);
    if (!Number.isInteger(m) || !Number.isInteger(sec) || m < 0 || sec < 0 || sec > 59) return 0;
    const total = m * 60 + sec;
    if (total <= 0 || total > 86400) return 0;
    return Math.floor(total / 60) * s.rate;
  }
  const n = Number(steps);
  return Number.isInteger(n) && n > 0 && n <= 200000 ? Math.floor(n / 100) : 0;
}

export const fmt = (n) => new Intl.NumberFormat("en-IN").format(n ?? 0);

export function describeValue(a) {
  if (a.metricType === "distance") return `${a.normalized.distanceKm} km`;
  if (a.metricType === "duration") return `${a.value} min`;
  return `${fmt(a.value)} steps`;
}
