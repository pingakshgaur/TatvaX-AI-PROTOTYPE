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
  const [celebrations, setCelebrations] = useState([]);
  const [xpPop, setXpPop] = useState(null);
  const [sound, setSoundState] = useState(() => readStorage("tatvax.sound") !== "off");
  const [progressVersion, setProgressVersion] = useState(0);
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

  // Rewards from a question or assessment: a quick XP pop, then full-screen celebrations for
  // each achievement, a level-up and a completed daily goal, shown one after another.
  const celebrate = useCallback((reward) => {
    if (!reward) return;
    if (reward.xp_gained > 0) {
      const id = ++toastId.current;
      setXpPop({ id, amount: reward.xp_gained });
      setTimeout(() => setXpPop((pop) => (pop?.id === id ? null : pop)), 1900);
    }
    const queue = [
      ...(reward.badges || []).map((badge) => ({ type: "badge", badge })),
      ...(reward.level_up ? [{ type: "level", level: reward.level_up }] : []),
      ...(reward.goal?.reached_now ? [{ type: "goal", goal: reward.goal }] : []),
    ].map((item) => ({ ...item, id: ++toastId.current }));
    if (queue.length) setCelebrations((list) => [...list, ...queue]);
    if (reward.progress) {
      if (user) setUserState((current) => (current ? { ...current, ...reward.progress } : current));
      else refreshUser();
    }
    setProgressVersion((v) => v + 1);
  }, [refreshUser, user]);

  const dismissCelebration = useCallback(() => setCelebrations((list) => list.slice(1)), []);

  const setSound = useCallback((on) => {
    setSoundState(on);
    writeStorage("tatvax.sound", on ? "on" : "off");
  }, []);

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
    app, user, lang, t, online, toasts, bootError, celebrations, xpPop, sound, progressVersion,
    setUser, setLang, notify, celebrate, dismissCelebration, setSound, refreshUser, reloadApp, languageInfo, retryBoot: boot,
  }), [app, user, lang, t, online, toasts, bootError, celebrations, xpPop, sound, progressVersion, setUser, setLang, notify,
    celebrate, dismissCelebration, setSound, refreshUser, reloadApp, languageInfo, boot]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const value = useContext(AppContext);
  if (!value) throw new Error("useApp must be used inside AppProvider");
  return value;
}
