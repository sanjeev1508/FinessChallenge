import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { ErrorBox } from "../components/Status.jsx";

export default function Register({ setUserId }) {
  const nav = useNavigate();
  const [form, setForm] = useState({ firstName: "", lastName: "", email: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const user = await api.register({ ...form, email: form.email.trim() || null });
      setUserId(user.userId);
      nav("/log", { state: { welcome: user.firstName } });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const existingId = error?.code === "DUPLICATE_USER" ? error.extra.existingUserId : null;

  return (
    <section className="narrow" aria-labelledby="join-title">
      <h1 id="join-title" className="display">Join the challenge</h1>
      <p className="lede">One entry per person. Your first and last name identify you on the board.</p>
      <form className="form" onSubmit={submit} noValidate>
        <div className="row-2">
          <label>First name
            <input required maxLength={50} autoComplete="given-name" value={form.firstName} onChange={set("firstName")} />
          </label>
          <label>Last name
            <input required maxLength={50} autoComplete="family-name" value={form.lastName} onChange={set("lastName")} />
          </label>
        </div>
        <label><span>Email <span className="optional">optional</span></span>
          <input type="email" maxLength={254} autoComplete="email" value={form.email} onChange={set("email")} />
        </label>
        <ErrorBox error={error} />
        {existingId && (
          <button type="button" className="btn ghost" onClick={() => { setUserId(existingId); nav("/dashboard"); }}>
            That's me, open my dashboard
          </button>
        )}
        <button className="btn primary" disabled={busy}>{busy ? "Joining…" : "Join challenge"}</button>
      </form>
    </section>
  );
}
