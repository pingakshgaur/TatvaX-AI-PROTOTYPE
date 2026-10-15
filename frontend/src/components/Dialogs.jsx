import { LogOut } from "lucide-react";
import { useEffect, useState } from "react";

import { applyTheme, useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { Dialog } from "./ui.jsx";

const THEMES = [
  ["system", ["#f5f3ee", "#161a1d", "#0f5a57"]],
  ["light", ["#f5f3ee", "#ffffff", "#0f5a57"]],
  ["dark", ["#0f1214", "#1e2327", "#5fb3a8"]],
  ["warm", ["#f3ecdf", "#fbf7ef", "#7a3e12"]],
  ["contrast", ["#ffffff", "#000000", "#00474a"]],
];

function currentTheme(user) {
  let saved = null;
  try { saved = localStorage.getItem("tatvax.theme"); } catch { /* unavailable */ }
  return user?.theme || saved || "system";
}

function ThemePicker({ value, onChange }) {
  const { t } = useApp();
  return (
    <div className="theme-options" role="group" aria-label={t("theme")}>
      {THEMES.map(([name, colors]) => (
        <button key={name} type="button" className="theme-option" aria-pressed={value === name}
          onClick={() => { onChange(name); applyTheme(name); }}>
          <span className="swatches">{colors.map((c) => <i key={c} style={{ background: c }} />)}</span>
          {t(`theme_${name}`)}
        </button>
      ))}
    </div>
  );
}

function useSubmit(handler) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await handler(Object.fromEntries(new FormData(event.currentTarget)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return { error, busy, submit };
}

function SignInForm({ onDone }) {
  const { t, setUser, notify } = useApp();
  const { error, busy, submit } = useSubmit(async (data) => {
    const res = await api("/api/auth/login", { method: "POST", body: data });
    setUser(res.user);
    applyTheme(res.user.theme);
    notify(`Signed in as ${res.user.name}`, { kind: "success" });
    onDone();
  });
  return (
    <form onSubmit={submit} noValidate>
      <div className="field"><label className="label" htmlFor="login-email">{t("email")}</label>
        <input className="input" id="login-email" name="email" type="email" autoComplete="email" required /></div>
      <div className="field"><label className="label" htmlFor="login-password">{t("password")}</label>
        <input className="input" id="login-password" name="password" type="password" autoComplete="current-password" required /></div>
      <p className="form-error" role="alert">{error}</p>
      <button className="btn btn-block btn-lg" type="submit" disabled={busy}>{t("sign_in")}</button>
    </form>
  );
}

function RegisterForm({ onDone }) {
  const { t, lang, setUser, notify } = useApp();
  const { error, busy, submit } = useSubmit(async (data) => {
    const res = await api("/api/auth/register", { method: "POST", body: { ...data, language: lang } });
    setUser(res.user);
    notify(res.user.role === "teacher" ? "Teacher account created" : `Welcome, ${res.user.name}`, { kind: "success" });
    onDone();
  });
  return (
    <form onSubmit={submit} noValidate>
      <div className="field"><label className="label" htmlFor="reg-name">{t("name")}</label>
        <input className="input" id="reg-name" name="name" autoComplete="name" maxLength={40} required /></div>
      <div className="field"><label className="label" htmlFor="reg-email">{t("email")}</label>
        <input className="input" id="reg-email" name="email" type="email" autoComplete="email" required /></div>
      <div className="field"><label className="label" htmlFor="reg-password">{t("password")}</label>
        <input className="input" id="reg-password" name="password" type="password" autoComplete="new-password" minLength={8} required />
        <span className="hint">At least 8 characters.</span></div>
      <div className="field"><label className="label" htmlFor="reg-code">{t("teacher_code")}</label>
        <input className="input" id="reg-code" name="teacher_code" autoComplete="off" />
        <span className="hint">Only for staff. The first account on a new installation becomes the administrator.</span></div>
      <p className="form-error" role="alert">{error}</p>
      <button className="btn btn-block btn-lg" type="submit" disabled={busy}>{t("create_account")}</button>
    </form>
  );
}

function SettingsForm({ onDone }) {
  const { t, user, setUser, notify } = useApp();
  const [theme, setTheme] = useState(currentTheme(user));
  const registered = user && !user.is_guest;
  const { error, busy, submit } = useSubmit(async (data) => {
    const body = { grade: data.grade ? Number(data.grade) : null, theme };
    if (registered) {
      body.name = data.name;
      body.leaderboard = Boolean(data.leaderboard);
    }
    const res = await api("/api/me", { method: "PATCH", body });
    setUser(res.user);
    notify("Settings saved", { kind: "success" });
    onDone();
  });
  const signOut = async () => {
    await api("/api/auth/logout", { method: "POST", body: {} });
    setUser(null);
    notify("Signed out");
    onDone();
  };
  return (
    <form onSubmit={submit} noValidate>
      {registered && (
        <div className="field"><label className="label" htmlFor="set-name">{t("name")}</label>
          <input className="input" id="set-name" name="name" defaultValue={user.name} maxLength={40} /></div>
      )}
      <div className="field"><label className="label" htmlFor="set-grade">{t("class_grade")}</label>
        <select className="select" id="set-grade" name="grade" defaultValue={user?.grade ?? ""}>
          <option value="">Not specified</option>
          {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => <option key={g} value={g}>Class {g}</option>)}
        </select>
        <span className="hint">The tutor adjusts its explanations to your class.</span></div>
      <div className="field"><span className="label">{t("theme")}</span><ThemePicker value={theme} onChange={setTheme} /></div>
      {registered && (
        <label className="field" style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <input type="checkbox" name="leaderboard" defaultChecked={user.leaderboard} />
          <span>{t("show_leaderboard")}</span>
        </label>
      )}
      <p className="form-error" role="alert">{error}</p>
      <div className="dialog-footer" style={{ justifyContent: registered ? "space-between" : "flex-end" }}>
        {registered && <button className="btn btn-ghost" type="button" onClick={signOut}><LogOut size={16} /> {t("sign_out")}</button>}
        <button className="btn" type="submit" disabled={busy}>{t("save")}</button>
      </div>
    </form>
  );
}

export function AccountDialog({ open, onClose, initialTab }) {
  const { t, user } = useApp();
  const registered = user && !user.is_guest;
  const tabs = registered ? ["settings"] : ["login", "register", "settings"];
  const [tab, setTab] = useState(tabs[0]);
  useEffect(() => {
    if (open) setTab(initialTab && tabs.includes(initialTab) ? initialTab : tabs[0]);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  const labels = { login: t("sign_in"), register: t("create_account"), settings: t("settings") };

  return (
    <Dialog open={open} onClose={onClose} title={registered ? user.name : t("account")}>
      {!registered && <p className="hint" style={{ marginTop: 0 }}>{t("guest_note")}</p>}
      {tabs.length > 1 && (
        <div className="segmented" role="group" style={{ marginBottom: 18, display: "flex" }}>
          {tabs.map((name) => (
            <button key={name} type="button" style={{ flex: 1 }} aria-pressed={tab === name} onClick={() => setTab(name)}>{labels[name]}</button>
          ))}
        </div>
      )}
      {tab === "login" && <SignInForm onDone={onClose} />}
      {tab === "register" && <RegisterForm onDone={onClose} />}
      {tab === "settings" && <SettingsForm onDone={onClose} />}
    </Dialog>
  );
}

export function FeedbackDialog({ open, onClose }) {
  const { t, user, notify } = useApp();
  const [rating, setRating] = useState(null);
  const { error, busy, submit } = useSubmit(async (data) => {
    await api("/api/feedback", { method: "POST", body: { message: data.message, name: data.name, rating, page: location.pathname } });
    notify(t("feedback_thanks"), { kind: "success" });
    setRating(null);
    onClose();
  });
  return (
    <Dialog open={open} onClose={onClose} title={t("feedback_title")}>
      <form onSubmit={submit} noValidate>
        <div className="field"><span className="label">Rating</span>
          <div className="rating" role="group" aria-label="Rating out of 5">
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} type="button" aria-pressed={rating === n} onClick={() => setRating(n)}>{n}</button>
            ))}
          </div></div>
        <div className="field"><label className="label" htmlFor="fb-message">{t("feedback_message")}</label>
          <textarea className="textarea" id="fb-message" name="message" required maxLength={3000} /></div>
        <div className="field"><label className="label" htmlFor="fb-name">{t("name")} <span className="hint">(optional)</span></label>
          <input className="input" id="fb-name" name="name" maxLength={80} defaultValue={user && !user.is_guest ? user.name : ""} /></div>
        <p className="form-error" role="alert">{error}</p>
        <div className="dialog-footer"><button className="btn" type="submit" disabled={busy}>Send feedback</button></div>
      </form>
    </Dialog>
  );
}
