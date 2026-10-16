// Theme switch at the foot of the sidebar: one icon per theme, with a sliding highlight.
import { Contrast, Monitor, Moon, Sun, Sunset } from "lucide-react";
import { useEffect, useState } from "react";

import { applyTheme, currentTheme, useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";

const THEMES = [
  ["system", Monitor],
  ["light", Sun],
  ["dark", Moon],
  ["warm", Sunset],
  ["contrast", Contrast],
];

export default function ThemeSwitch() {
  const { t, user, setUser } = useApp();
  const [theme, setTheme] = useState(() => user?.theme || currentTheme());

  // Stay in step when the theme is changed elsewhere (Settings, signing in).
  useEffect(() => {
    const sync = (event) => setTheme(event.detail);
    window.addEventListener("tatvax-theme", sync);
    return () => window.removeEventListener("tatvax-theme", sync);
  }, []);

  const choose = (name) => {
    if (name === theme) return;
    applyTheme(name, { animate: true });
    if (user) {
      api("/api/me", { method: "PATCH", body: { theme: name } }).then((res) => setUser(res.user)).catch(() => {});
    }
  };

  const index = Math.max(0, THEMES.findIndex(([name]) => name === theme));

  return (
    <div className="sidebar-footer theme-footer">
      <div className="theme-switch-head">
        <span className="eyebrow">{t("theme")}</span>
        <span className="theme-switch-name">{t(`theme_${theme}`)}</span>
      </div>
      <div className="theme-switch" role="radiogroup" aria-label={t("theme")} style={{ "--i": index, "--n": THEMES.length }}>
        <span className="theme-switch-thumb" aria-hidden="true" />
        {THEMES.map(([name, Icon]) => (
          <button key={name} type="button" role="radio" aria-checked={theme === name}
            aria-label={t(`theme_${name}`)} title={t(`theme_${name}`)} onClick={() => choose(name)}>
            <Icon size={16} strokeWidth={1.9} aria-hidden="true" />
          </button>
        ))}
      </div>
    </div>
  );
}
