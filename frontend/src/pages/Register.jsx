import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, setAccessToken } from "../api.js";
import { ErrorBox } from "../components/Status.jsx";

export default function Register({ setUserId }) {
  const nav = useNavigate();
  const [form, setForm] = useState({ firstName: "", lastName: "", email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const session = await api.register({ ...form, email: form.email.trim() });
      setAccessToken(session.accessToken);
      setUserId(session.user.userId);
      nav("/dashboard");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="narrow" aria-labelledby="join-title">
      <h1 id="join-title" className="display">Join the challenge</h1>
      <p className="lede">Create an account to join the challenge and log your activities.</p>
      <form className="form" onSubmit={submit}>
        <div className="row-2">
          <label>First name
            <input required maxLength={50} autoComplete="given-name" value={form.firstName} onChange={set("firstName")} />
          </label>
          <label>Last name
            <input required maxLength={50} autoComplete="family-name" value={form.lastName} onChange={set("lastName")} />
          </label>
        </div>
        <label>Email
          <input required type="email" maxLength={254} autoComplete="email" value={form.email} onChange={set("email")} />
        </label>
        <label>Password
          <input required type="password" minLength={8} maxLength={128} autoComplete="new-password" aria-describedby="password-help"
                 value={form.password} onChange={set("password")} />
          <span id="password-help" className="fineprint">Use 8 to 128 characters.</span>
        </label>
        <ErrorBox error={error} />
        <button className="btn primary" disabled={busy}>{busy ? "Joining…" : "Join challenge"}</button>
      </form>
      <p className="fineprint">Already have an account? <Link to="/login">Log in</Link>.</p>
    </section>
  );
}
