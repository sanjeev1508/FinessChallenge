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
    const metres = Math.round(Number(km) * 1000);
    return Number.isFinite(metres) && metres > 0 ? Math.floor((metres * s.rate) / 1000) : 0;
  }
  if (s.metric === "duration") {
    const total = (Number(minutes) || 0) * 60 + (Number(seconds) || 0);
    return Math.floor(total / 60) * s.rate;
  }
  const n = Number(steps);
  return Number.isInteger(n) && n > 0 ? Math.floor(n / 100) : 0;
}

export const fmt = (n) => new Intl.NumberFormat("en-IN").format(n ?? 0);

export function describeValue(a) {
  if (a.metricType === "distance") return `${a.normalized.distanceKm} km`;
  if (a.metricType === "duration") return `${a.value} min`;
  return `${fmt(a.value)} steps`;
}
