import { useState } from "react";
import { api } from "../api.js";

export default function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [form, setForm] = useState({ email: "", password: "", organization_name: "", display_name: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result =
        mode === "login"
          ? await api.login({ email: form.email, password: form.password })
          : await api.signup(form);
      onAuthenticated({ ...result, email: form.email });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-mark">EKIP</div>
        <h1>{mode === "login" ? "Welcome back" : "Set up your desk"}</h1>
        <p className="auth-sub">
          {mode === "login" ? "Sign in to your knowledge desk." : "Create an organization and your account."}
        </p>

        {error && <div className="auth-error">{error}</div>}

        <div className="field">
          <label>Email</label>
          <input type="email" required value={form.email} onChange={update("email")} placeholder="you@company.com" />
        </div>
        <div className="field">
          <label>Password</label>
          <input type="password" required value={form.password} onChange={update("password")} placeholder="••••••••" />
        </div>

        {mode === "signup" && (
          <>
            <div className="field">
              <label>Your name</label>
              <input value={form.display_name} onChange={update("display_name")} placeholder="Optional" />
            </div>
            <div className="field">
              <label>Organization name</label>
              <input required value={form.organization_name} onChange={update("organization_name")} placeholder="Acme Inc." />
            </div>
          </>
        )}

        <button className="btn" type="submit" disabled={busy} style={{ width: "100%", marginTop: 6 }}>
          {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
        </button>

        <div className="auth-switch">
          {mode === "login" ? (
            <>No account yet? <a className="btn-text" onClick={() => setMode("signup")} style={{ display: "inline" }}>Create one</a></>
          ) : (
            <>Already set up? <a className="btn-text" onClick={() => setMode("login")} style={{ display: "inline" }}>Sign in</a></>
          )}
        </div>
      </form>
    </div>
  );
}
