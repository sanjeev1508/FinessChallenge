import { useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api, requestId } from "../api.js";
import { SPORTS, SPORT_KEYS, describeValue, fmt, previewPoints } from "../sports.js";
import { ErrorBox } from "../components/Status.jsx";
import UserPicker from "../components/UserPicker.jsx";

const todayISO = () => {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};

export default function LogActivity({ userId, setUserId }) {
  const welcome = useLocation().state?.welcome;
  const [sport, setSport] = useState("running");
  const [km, setKm] = useState("");
  const [minutes, setMinutes] = useState("");
  const [seconds, setSeconds] = useState("");
  const [steps, setSteps] = useState("");
  const [date, setDate] = useState(todayISO());
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(null);
  // One key per form submission: retries/double-clicks can't double count.
  const [reqId, setReqId] = useState(requestId);

  const meta = SPORTS[sport];
  const preview = useMemo(() => previewPoints(sport, { km, minutes, seconds, steps }),
    [sport, km, minutes, seconds, steps]);

  function buildValue() {
    if (meta.metric === "distance") return km === "" ? null : Number(km);
    if (meta.metric === "duration") {
      if (minutes === "" && seconds === "") return null;
      return `${Number(minutes) || 0}:${String(Number(seconds) || 0).padStart(2, "0")}`;
    }
    return steps === "" ? null : Number(steps);
  }

  async function submit(e) {
    e.preventDefault();
    if (!userId) return setError({ message: "Choose who you are first." });
    const value = buildValue();
    if (value === null) return setError({ message: `Enter your ${meta.metric === "count" ? "steps" : meta.metric}.` });
    setBusy(true); setError(null);
    try {
      const a = await api.logActivity({
        userId, sport, metricType: meta.metric, value, activityDate: date,
        notes: notes.trim() || null, clientRequestId: reqId,
      });
      setSaved(a);
      setKm(""); setMinutes(""); setSeconds(""); setSteps(""); setNotes("");
      setReqId(requestId());
    } catch (err) {
      setError(err);
      if (err.status === 400 || err.status === 409) setReqId(requestId());
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="narrow" aria-labelledby="log-title">
      <h1 id="log-title" className="display">{welcome ? `Welcome, ${welcome}` : "Log activity"}</h1>
      <p className="lede">Pick a sport, enter what you did, and the points land on the board instantly.</p>

      <UserPicker value={userId} onChange={setUserId} />

      <form className="form" onSubmit={submit} noValidate>
        <fieldset className="sport-grid">
          <legend>Sport</legend>
          {SPORT_KEYS.map((k) => (
            <label key={k} className={`sport-chip ${sport === k ? "on" : ""}`} style={{ "--c": SPORTS[k].color }}>
              <input type="radio" name="sport" value={k} checked={sport === k}
                     onChange={() => { setSport(k); setError(null); }} />
              <span className="chip-name">{SPORTS[k].label}</span>
              <span className="chip-rate">
                {k === "steps" ? "1 pt / 100 steps" : `${SPORTS[k].rate} pts / ${SPORTS[k].unit}`}
              </span>
            </label>
          ))}
        </fieldset>

        {meta.metric === "distance" && (
          <label>Distance in km
            <input inputMode="decimal" type="number" min="0.001" max="1000" step="0.001" placeholder="e.g. 5.25"
                   value={km} onChange={(e) => setKm(e.target.value)} />
          </label>
        )}
        {meta.metric === "duration" && (
          <div className="row-2">
            <label>Minutes
              <input inputMode="numeric" type="number" min="0" max="1440" step="1" placeholder="45"
                     value={minutes} onChange={(e) => setMinutes(e.target.value)} />
            </label>
            <label>Seconds
              <input inputMode="numeric" type="number" min="0" max="59" step="1" placeholder="30"
                     value={seconds} onChange={(e) => setSeconds(e.target.value)} />
            </label>
          </div>
        )}
        {meta.metric === "count" && (
          <label>Steps today
            <input inputMode="numeric" type="number" min="1" max="200000" step="1" placeholder="e.g. 8500"
                   value={steps} onChange={(e) => setSteps(e.target.value)} />
            <small className="hint">One steps entry per day. Only full blocks of 100 count.</small>
          </label>
        )}

        <div className="row-2">
          <label>Date
            <input type="date" value={date} max={todayISO()} onChange={(e) => setDate(e.target.value)} />
          </label>
          <label><span>Note <span className="optional">optional</span></span>
            <input maxLength={280} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Morning loop" />
          </label>
        </div>

        <div className="preview" aria-live="polite">
          <span className="preview-pts" style={{ color: meta.color }}>{fmt(preview)}</span>
          <span>points for this {meta.label.toLowerCase()} entry</span>
        </div>

        <ErrorBox error={error} />
        <button className="btn primary" disabled={busy}>{busy ? "Saving…" : "Save activity"}</button>
      </form>

      {saved && (
        <div className="saved" role="status">
          Saved {SPORTS[saved.sport].label.toLowerCase()}, {describeValue(saved)}: <b>+{fmt(saved.points)} points</b>.{" "}
          <Link to="/">See the standings</Link> or <Link to="/dashboard">your dashboard</Link>.
        </div>
      )}
    </section>
  );
}
