import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { SPORTS, SPORT_KEYS, describeValue, fmt } from "../sports.js";
import { ErrorBox, Loading } from "../components/Status.jsx";
import UserPicker from "../components/UserPicker.jsx";

const WINDOWS = [14, 30, 90];
const VOLUME = {
  cumulative: { label: "Total points", key: "points", unit: "pts" },
  distanceKm: { label: "Distance", key: "distanceKm", unit: "km" },
  durationMinutes: { label: "Minutes", key: "durationMinutes", unit: "min" },
  stepCount: { label: "Steps", key: "stepCount", unit: "steps" },
};

const shortDate = (iso) => new Date(iso + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short" });
const axis = { fontSize: 12, fill: "var(--ink-soft)" };

function Stat({ value, label, sub }) {
  return (
    <div className="stat">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
      {sub && <span className="stat-sub">{sub}</span>}
    </div>
  );
}

export default function Dashboard({ userId, setUserId }) {
  const { id: routeId } = useParams();
  const nav = useNavigate();
  const viewing = routeId || userId;
  const isMe = viewing && viewing === userId;
  const [days, setDays] = useState(30);
  const [volume, setVolume] = useState("cumulative");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    if (!viewing) return;
    setError(null);
    api.dashboard(viewing, days).then(setData).catch((e) => {
      setError(e);
      if (e.status === 404 && isMe) setUserId(null);   // stale saved id
    });
  }, [viewing, days, isMe, setUserId]);

  useEffect(() => { setData(null); }, [viewing]);
  useEffect(() => { load(); }, [load]);

  const pie = useMemo(() => (data?.bySport ?? []).filter((s) => s.points > 0), [data]);
  const volumeData = useMemo(() => {
    if (!data) return [];
    return volume === "cumulative" ? data.cumulative : data.timeline.map((t) => ({ date: t.date, value: t[volume] }));
  }, [data, volume]);

  if (!viewing) {
    return (
      <section className="narrow">
        <h1 className="display">My dashboard</h1>
        <p className="lede">Choose your name to see your history, or join if you're new.</p>
        <UserPicker value={null} onChange={setUserId} />
      </section>
    );
  }
  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!data) return <Loading what="Loading dashboard" />;

  const { user, summary } = data;
  const hasData = summary.activityCount > 0;
  const rankSub = summary.rankChange > 0 ? `▲ ${summary.rankChange} this week`
    : summary.rankChange < 0 ? `▼ ${-summary.rankChange} this week` : `of ${summary.totalUsers}`;

  return (
    <section aria-labelledby="dash-title">
      <div className="dash-head">
        <div>
          <h1 id="dash-title" className="display">{user.firstName} {user.lastName}</h1>
          <p className="lede">
            {isMe ? "Your" : `${user.firstName}'s`} training history
            {summary.favouriteSport && <>, mostly {SPORTS[summary.favouriteSport].label.toLowerCase()}</>}
          </p>
        </div>
        <div className="dash-actions">
          {!isMe && <button className="btn ghost" onClick={() => { setUserId(user.userId); nav("/dashboard"); }}>This is me</button>}
          {isMe && <Link className="btn primary" to="/log">Log activity</Link>}
        </div>
      </div>

      <div className="stats">
        <Stat value={summary.rank ? `#${summary.rank}` : "–"} label="Rank" sub={rankSub} />
        <Stat value={fmt(summary.totalPoints)} label="Total points" sub={`+${fmt(summary.pointsLast7Days)} in 7 days`} />
        <Stat value={summary.currentStreakDays} label="Day streak" sub={`${summary.activeDays} active days`} />
        <Stat value={summary.activityCount} label="Activities" />
      </div>

      {!hasData ? (
        <div className="empty-card">
          <p>No activities yet, so there's nothing to chart.</p>
          {isMe && <Link className="btn primary" to="/log">Log your first activity</Link>}
        </div>
      ) : (
        <>
          <div className="panel">
            <div className="panel-head">
              <h2>Activity history</h2>
              <div className="segmented" role="group" aria-label="Time window">
                {WINDOWS.map((w) => <button key={w} aria-pressed={days === w} onClick={() => setDays(w)}>{w} days</button>)}
              </div>
            </div>
            <p className="panel-note">Points earned each day, by sport.</p>
            <div className="chart">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.timeline} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--line)" />
                  <XAxis dataKey="date" tickFormatter={shortDate} tick={axis} minTickGap={24} />
                  <YAxis tick={axis} allowDecimals={false} />
                  <Tooltip labelFormatter={shortDate} formatter={(v, n) => [fmt(v), SPORTS[n]?.label ?? n]}
                           cursor={{ fill: "var(--chalk-2)" }} />
                  <Legend formatter={(n) => SPORTS[n]?.label ?? n} iconType="square" wrapperStyle={{ fontSize: 13 }} />
                  {SPORT_KEYS.map((s) => <Bar key={s} dataKey={s} stackId="pts" fill={SPORTS[s].color} maxBarSize={28} />)}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid-2">
            <div className="panel">
              <div className="panel-head">
                <h2>Volume over time</h2>
                <div className="segmented small" role="group" aria-label="Measure">
                  {Object.entries(VOLUME).map(([k, v]) => (
                    <button key={k} aria-pressed={volume === k} onClick={() => setVolume(k)}>{v.label}</button>
                  ))}
                </div>
              </div>
              <p className="panel-note">
                {volume === "cumulative" ? "Running total of points."
                  : volume === "durationMinutes" ? "Full recorded duration in minutes, including seconds."
                  : `Daily ${VOLUME[volume].label.toLowerCase()} (${VOLUME[volume].unit}).`}
              </p>
              <div className="chart">
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={volumeData} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="var(--line)" />
                    <XAxis dataKey="date" tickFormatter={shortDate} tick={axis} minTickGap={24} />
                    <YAxis tick={axis} />
                    <Tooltip labelFormatter={shortDate} formatter={(v) => [`${fmt(v)} ${VOLUME[volume].unit}`, VOLUME[volume].label]} />
                    <Area type="monotone" dataKey={volume === "cumulative" ? "points" : "value"}
                          stroke="var(--signal)" strokeWidth={2} fill="var(--signal-tint)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="panel">
              <div className="panel-head"><h2>Sport mix</h2></div>
              <p className="panel-note">Share of all-time points.</p>
              <div className="mix">
                <div className="chart donut">
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={pie} dataKey="points" nameKey="sport" innerRadius="58%" outerRadius="92%"
                           paddingAngle={1.5} stroke="none">
                        {pie.map((s) => <Cell key={s.sport} fill={SPORTS[s.sport].color} />)}
                      </Pie>
                      <Tooltip formatter={(v, n) => [`${fmt(v)} pts`, SPORTS[n]?.label]} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <ul className="mix-list">
                  {data.bySport.filter((s) => s.count > 0).sort((a, b) => b.points - a.points).map((s) => (
                    <li key={s.sport}>
                      <span className="swatch" style={{ background: SPORTS[s.sport].color }} />
                      <span className="mix-name">{SPORTS[s.sport].label}</span>
                      <span className="mix-pct">{summary.totalPoints > 0 ? Math.round((s.points / summary.totalPoints) * 100) : 0}%</span>
                      <small>
                        {s.count} {s.count === 1 ? "session" : "sessions"},{" "}
                        {SPORTS[s.sport].metric === "distance" ? `${fmt(Math.round(s.distanceKm))} km`
                          : SPORTS[s.sport].metric === "duration" ? `${fmt(s.durationMinutes)} min`
                          : `${fmt(s.steps)} steps`}
                      </small>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head"><h2>Recent activities</h2></div>
            <div className="table-wrap">
              <table className="recent">
                <thead><tr><th>Date</th><th>Sport</th><th>Logged</th><th className="num">Points</th></tr></thead>
                <tbody>
                  {data.recentActivities.map((a) => (
                    <tr key={a.activityId}>
                      <td>{shortDate(a.activityDate)}</td>
                      <td><span className="dot" style={{ background: SPORTS[a.sport].color }} />{SPORTS[a.sport].label}</td>
                      <td>{describeValue(a)}{a.notes && <small className="note"> {a.notes}</small>}</td>
                      <td className="num">+{fmt(a.points)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
