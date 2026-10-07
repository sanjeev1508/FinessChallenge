import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { fmt } from "../sports.js";
import { ErrorBox, Loading } from "../components/Status.jsx";
import { useApiRead } from "../useApiRead.js";
import { formatDate } from "../calendar.js";

const PERIODS = [{ days: 7, label: "This week" }, { days: 30, label: "30 days" }];

function Trend({ entry }) {
  if (entry.trend === "new") return <span className="trend new" title="Joined after the comparison date">New</span>;
  if (entry.trend === "same") return <span className="trend same" title="No change">–</span>;
  const up = entry.rankChange > 0;
  return (
    <span className={`trend ${up ? "up" : "down"}`}
          title={`${up ? "Up" : "Down"} ${Math.abs(entry.rankChange)} from #${entry.previousRank}`}>
      <span aria-hidden="true">{up ? "▲" : "▼"}</span>{Math.abs(entry.rankChange)}
      <span className="sr-only">{up ? " places up" : " places down"}</span>
    </span>
  );
}

export default function Leaderboard({ currentUserId }) {
  const [period, setPeriod] = useState(7);
  const [query, setQuery] = useState("");
  const request = useCallback((signal) => api.leaderboard(period, { signal }), [period]);
  const { data, error, load } = useApiRead(request);

  useEffect(() => {
    const t = setInterval(load, 30000);          // keep standings fresh
    window.addEventListener("focus", load);
    return () => { clearInterval(t); window.removeEventListener("focus", load); };
  }, [load]);

  const entries = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = data?.entries ?? [];
    return q ? list.filter((e) => `${e.firstName} ${e.lastName}`.toLowerCase().includes(q)) : list;
  }, [data, query]);

  const leader = data?.entries?.[0];

  return (
    <section aria-labelledby="lb-title">
      <div className="lb-head">
        <div>
          <h1 id="lb-title" className="display">Standings</h1>
          <p className="lede">
            Every sport converts to points, so a swimmer and a walker race on the same board.
            {leader && leader.totalPoints > 0 && <> {leader.firstName} leads with {fmt(leader.totalPoints)} points.</>}
          </p>
        </div>
        <div className="lb-controls">
          <div className="segmented" role="group" aria-label="Trend period">
            {PERIODS.map((p) => (
              <button key={p.days} aria-pressed={period === p.days} onClick={() => setPeriod(p.days)}>{p.label}</button>
            ))}
          </div>
          <input className="search" type="search" placeholder="Find a name" value={query}
                 onChange={(e) => setQuery(e.target.value)} aria-label="Filter by name" />
        </div>
      </div>

      <ErrorBox error={error} onRetry={load} />
      {!data && !error && <Loading what="Loading standings" />}

      {data && (
        <ol className="board" aria-label="Leaderboard">
          <li className="board-row board-labels" aria-hidden="true">
            <span>Rank</span><span>Athlete</span><span>Move</span>
            <span className="num">{period === 7 ? "Logged in 7 days" : "Logged in 30 days"}</span>
            <span className="num">Total points</span>
          </li>
          {entries.length === 0 && (
            <li className="empty">
              {query ? "No one matches that name." : <>No athletes yet. <Link to="/join">Be the first to join</Link>.</>}
            </li>
          )}
          {entries.map((e) => (
            <li key={e.userId}
                className={`board-row ${e.rank <= 3 && e.totalPoints > 0 ? `medal-${e.rank}` : ""} ${e.userId === currentUserId ? "is-me" : ""}`}>
              <span className="rank">{e.rank}</span>
              <span className="athlete">
                <Link to={`/dashboard/${e.userId}`}>{e.firstName} {e.lastName}</Link>
                {e.userId === currentUserId && <span className="you">You</span>}
                <small>{e.activityCount} {e.activityCount === 1 ? "activity" : "activities"}</small>
              </span>
              <span><Trend entry={e} /></span>
              <span className="num gained">{e.pointsInPeriod > 0 ? `+${fmt(e.pointsInPeriod)}` : "0"}</span>
              <span className="num total">{fmt(e.totalPoints)}</span>
            </li>
          ))}
        </ol>
      )}
      {data && (
        <p className="fineprint">
          Ties share a rank. Movement compares today with standings at the end of {formatDate(data.comparedTo)} (UTC).
          Movement and period points use submission dates, not backdated workout dates. Updates every 30 seconds.
        </p>
      )}
    </section>
  );
}
