import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { api } from "../lib/api.js";
import { translate } from "../lib/i18n.js";

const AppContext = createContext(null);

function readStorage(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

function writeStorage(key, value) {
  try { localStorage.setItem(key, value); } catch { /* storage unavailable */ }
}

export function applyTheme(theme) {
  if (!theme || theme === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
  writeStorage("tatvax.theme", theme || "system");
}

export function AppProvider({ children }) {
  const [app, setApp] = useState(null);
  const [user, setUserState] = useState(null);
  const [lang, setLangState] = useState("en");
  const [bootError, setBootError] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [online, setOnline] = useState(navigator.onLine);
  const toastId = useRef(0);

  const boot = useCallback(async () => {
    setBootError(null);
    try {
      const data = await api("/api/bootstrap");
      setApp(data.app);
      setUserState(data.user);
      if (data.user?.theme) applyTheme(data.user.theme);
      const codes = data.app.languages.map((l) => l.code);
      const browser = (navigator.language || "en").split("-")[0];
      const preferred = data.user && !data.user.is_guest
        ? data.user.language
        : [data.user?.language, readStorage("tatvax.lang"), browser].find((c) => c && codes.includes(c));
      setLangState(preferred || "en");
    } catch (err) {
      setBootError(err.message);
    }
  }, []);

  useEffect(() => { boot(); }, [boot]);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const t = useCallback((key, vars) => translate(lang, key, vars), [lang]);

  const notify = useCallback((title, { detail = "", kind = "", duration = 3600 } = {}) => {
    const id = ++toastId.current;
    setToasts((list) => [...list, { id, title, detail, kind }]);
    setTimeout(() => setToasts((list) => list.filter((toast) => toast.id !== id)), duration);
  }, []);

  const setLang = useCallback((code) => {
    setLangState(code);
    writeStorage("tatvax.lang", code);
    api("/api/me", { method: "PATCH", body: { language: code } })
      .then((res) => setUserState(res.user))
      .catch(() => {});
  }, []);

  const setUser = useCallback((next) => {
    setUserState(next);
    if (next && !next.is_guest && next.language) setLangState(next.language);
  }, []);

  // Questions and quizzes create a guest profile on first use; pick it up quietly.
  const refreshUser = useCallback(async () => {
    const { user: fresh } = await api("/api/me").catch(() => ({}));
    if (fresh) setUserState(fresh);
  }, []);

  const celebrate = useCallback((reward) => {
    if (!reward) return;
    const beforeLevel = user?.level;
    if (reward.xp_gained > 0) notify(t("xp_gained", { n: reward.xp_gained }), { kind: "success" });
    (reward.badges || []).forEach((badge) =>
      notify(t("badge_earned"), { detail: `${badge.name}: ${badge.description}`, duration: 5200 }));
    if (reward.progress) {
      if (beforeLevel && reward.progress.level > beforeLevel) {
        notify(t("level_up", { level: reward.progress.level }), { duration: 5200 });
      }
      if (user) setUserState((current) => (current ? { ...current, ...reward.progress } : current));
      else refreshUser();
    }
  }, [notify, refreshUser, t, user]);

  const reloadApp = useCallback(async () => {
    const data = await api("/api/bootstrap");
    setApp(data.app);
  }, []);

  const languageInfo = useCallback(
    (code = lang) => app?.languages.find((l) => l.code === code)
      || { code: "en", name: "English", native: "English", speech: "en-IN", dir: "ltr" },
    [app, lang],
  );

  const value = useMemo(() => ({
    app, user, lang, t, online, toasts, bootError,
    setUser, setLang, notify, celebrate, refreshUser, reloadApp, languageInfo, retryBoot: boot,
  }), [app, user, lang, t, online, toasts, bootError, setUser, setLang, notify, celebrate, refreshUser, reloadApp, languageInfo, boot]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const value = useContext(AppContext);
  if (!value) throw new Error("useApp must be used inside AppProvider");
  return value;
}
