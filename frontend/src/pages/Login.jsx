import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, setAccessToken } from "../api.js";
import { ErrorBox } from "../components/Status.jsx";

export default function Login({ setUserId }) {
  const nav = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const session = await api.login({ email: form.email.trim(), password: form.password });
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
    <section className="narrow" aria-labelledby="login-title">
      <h1 id="login-title" className="display">Log in</h1>
      <p className="lede">Sign in to see your dashboard and log activities.</p>
      <form className="form" onSubmit={submit} noValidate>
        <label>Email
          <input required type="email" maxLength={254} autoComplete="email"
                 value={form.email} onChange={set("email")} />
        </label>
        <label>Password
          <input required type="password" maxLength={128} autoComplete="current-password"
                 value={form.password} onChange={set("password")} />
        </label>
        <ErrorBox error={error} />
        <button className="btn primary" disabled={busy}>{busy ? "Logging in…" : "Log in"}</button>
      </form>
      <p className="fineprint">New to the challenge? <Link to="/join">Create an account</Link>.</p>
    </section>
  );
}
