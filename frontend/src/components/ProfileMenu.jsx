// The student's avatar in the top bar: level ring, streak, and a menu with their account,
// progress, achievements, daily goal, theme, sound and sign-out.
import {
  Award, BarChart3, Flame, Languages, LogIn, LogOut, MessageSquareText, Minus, Plus, Settings, Trophy, UserPlus,
  Volume2, VolumeX,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { applyTheme, useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { formatNumber } from "../lib/format.js";

const THEMES = [
  ["system", "linear-gradient(135deg, #f5f3ee 50%, #161a1d 50%)"],
  ["light", "#f5f3ee"],
  ["dark", "#161a1d"],
  ["warm", "#f3ecdf"],
  ["contrast", "#000000"],
];

function AvatarRing({ progress = 0, initial }) {
  const r = 15;
  const c = 2 * Math.PI * r;
  return (
    <span className="avatar-ring" aria-hidden="true">
      <svg viewBox="0 0 34 34" width="100%" height="100%">
        <circle cx="17" cy="17" r={r} fill="none" stroke="var(--rule)" strokeWidth="2.5" />
        <circle cx="17" cy="17" r={r} fill="none" stroke="url(#ring-grad)" strokeWidth="2.5" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - progress)} style={{ transition: "stroke-dashoffset 0.8s" }} />
        <defs>
          <linearGradient id="ring-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#0e9f8e" /><stop offset="1" stopColor="#f2a516" />
          </linearGradient>
        </defs>
      </svg>
      <span className="face">{initial}</span>
    </span>
  );
}

export default function ProfileMenu({ onAccount, onFeedback }) {
  const { user, setUser, notify, t, sound, setSound, progressVersion } = useApp();
  const [open, setOpen] = useState(false);
  const [stats, setStats] = useState(null);
  const ref = useRef(null);
  const location = useLocation();
  const registered = user && !user.is_guest;
  const initial = registered ? user.name.trim().charAt(0).toUpperCase() : "G";
  const theme = user?.theme || (() => { try { return localStorage.getItem("tatvax.theme"); } catch { return null; } })() || "system";

  useEffect(() => {
    let live = true;
    api("/api/progress").then((res) => live && setStats(res.progress)).catch(() => {});
    return () => { live = false; };
  }, [user?.id, progressVersion, open]);

  useEffect(() => { setOpen(false); }, [location.pathname]);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (event) => { if (!ref.current?.contains(event.target)) setOpen(false); };
    const onKey = (event) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const patch = async (body) => {
    try {
      const res = await api("/api/me", { method: "PATCH", body });
      setUser(res.user);
      return res.user;
    } catch (err) {
      notify(err.message, { kind: "error" });
      return null;
    }
  };

  const changeGoal = async (delta) => {
    const goal = Math.max(1, Math.min(50, (stats?.goal.goal ?? 5) + delta));
    setStats((s) => (s ? { ...s, goal: { ...s.goal, goal, complete: s.goal.done >= goal } } : s));
    await patch({ daily_goal: goal });
  };

  const signOut = async () => {
    await api("/api/auth/logout", { method: "POST", body: {} });
    setUser(null);
    setOpen(false);
    notify("Signed out");
  };

  const level = stats?.level ?? user?.level ?? 1;
  const xp = stats?.xp ?? user?.xp ?? 0;
  const progress = stats?.progress ?? user?.progress ?? 0;
  const streak = stats?.streak.current ?? 0;
  const earned = stats ? stats.badges.filter((b) => b.earned).length : 0;
  const goal = stats?.goal ?? { done: 0, goal: user?.daily_goal ?? 5 };

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button type="button" className="profile-trigger" aria-haspopup="menu" aria-expanded={open}
        aria-label={`${registered ? user.name : t("guest")}, ${t("level")} ${level}`} onClick={() => setOpen((v) => !v)}>
        <AvatarRing progress={progress} initial={initial} />
        <span className="lvl">LV {level}</span>
        {streak > 0 && <span className="streak-pip"><Flame size={13} />{streak}</span>}
      </button>

      {open && (
        <div className="profile-menu" role="menu">
          <div className="profile-head">
            <div className="who">
              <AvatarRing progress={progress} initial={initial} />
              <div>
                <strong>{registered ? user.name : t("guest")}</strong>
                <span className="sub">{t("level")} {level}{user?.grade ? ` · Class ${user.grade}` : ""}{user?.role === "teacher" ? " · Teacher" : ""}</span>
              </div>
            </div>
            <div className="xp-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)} aria-label="XP to next level">
              <span style={{ width: `${Math.round(progress * 100)}%` }} />
            </div>
            <span className="sub">{formatNumber(xp)} XP · {formatNumber((stats?.next_level_xp ?? 100) - xp)} XP to level {level + 1}</span>
          </div>

          <div className="profile-stats">
            <div><b style={{ color: "var(--c-coral)" }}>{streak}</b><span>Day streak</span></div>
            <div><b style={{ color: "var(--c-plum)" }}>{earned}</b><span>Badges</span></div>
            <div><b style={{ color: "var(--c-indigo)" }}>{stats?.rank ? `#${stats.rank}` : "—"}</b><span>This week</span></div>
          </div>

          <div className="goal-row">
            <div className="goal-top">
              <span><b>Daily goal</b> · {Math.min(goal.done, goal.goal)}/{goal.goal} activities</span>
              <span className="stepper">
                <button type="button" aria-label="Lower daily goal" onClick={() => changeGoal(-1)}><Minus size={12} /></button>
                <button type="button" aria-label="Raise daily goal" onClick={() => changeGoal(1)}><Plus size={12} /></button>
              </span>
            </div>
            <div className="goal-bar"><span style={{ width: `${Math.min(100, (goal.done / goal.goal) * 100)}%` }} /></div>
          </div>

          <div className="menu-list">
            {registered ? (
              <button type="button" className="menu-item" role="menuitem" onClick={() => { setOpen(false); onAccount("settings"); }}>
                <span className="mi-icon" style={{ background: "var(--c-teal)" }}><Settings size={16} /></span> My account
              </button>
            ) : (
              <>
                <button type="button" className="menu-item" role="menuitem" onClick={() => { setOpen(false); onAccount("register"); }}>
                  <span className="mi-icon" style={{ background: "var(--c-teal)" }}><UserPlus size={16} /></span> Create a free account
                  <span className="mi-meta">Save progress</span>
                </button>
                <button type="button" className="menu-item" role="menuitem" onClick={() => { setOpen(false); onAccount("login"); }}>
                  <span className="mi-icon" style={{ background: "var(--c-indigo)" }}><LogIn size={16} /></span> Sign in
                </button>
              </>
            )}
            <Link to="/progress" className="menu-item" role="menuitem">
              <span className="mi-icon" style={{ background: "var(--c-indigo)" }}><BarChart3 size={16} /></span> My progress
            </Link>
            <Link to="/progress#achievements" className="menu-item" role="menuitem">
              <span className="mi-icon" style={{ background: "var(--c-plum)" }}><Award size={16} /></span> Achievements
              <span className="mi-meta">{earned}/{stats?.badges.length ?? 13}</span>
            </Link>
            <Link to="/progress#leaderboard" className="menu-item" role="menuitem">
              <span className="mi-icon" style={{ background: "var(--c-saffron)" }}><Trophy size={16} /></span> Leaderboard
              <span className="mi-meta">{stats?.rank ? `Rank #${stats.rank}` : ""}</span>
            </Link>
            <Link to="/translate" className="menu-item" role="menuitem">
              <span className="mi-icon" style={{ background: "var(--c-leaf)" }}><Languages size={16} /></span> Translator
              <span className="mi-meta"><kbd>Ctrl K</kbd></span>
            </Link>
            <div className="menu-sep" />
            <div className="menu-item" style={{ cursor: "default" }}>
              <span>Theme</span>
              <span className="theme-dots" role="group" aria-label="Theme">
                {THEMES.map(([name, swatch]) => (
                  <button key={name} type="button" aria-label={t(`theme_${name}`)} title={t(`theme_${name}`)} aria-pressed={theme === name}
                    style={{ background: swatch }} onClick={() => { applyTheme(name); if (user) patch({ theme: name }); }} />
                ))}
              </span>
            </div>
            <button type="button" className="menu-item" role="menuitemcheckbox" aria-checked={sound} onClick={() => setSound(!sound)}>
              {sound ? <Volume2 size={16} /> : <VolumeX size={16} />} Celebration sounds
              <span className="mi-meta">{sound ? "On" : "Off"}</span>
            </button>
            <button type="button" className="menu-item" role="menuitem" onClick={() => { setOpen(false); onFeedback(); }}>
              <MessageSquareText size={16} /> Send feedback
            </button>
            {registered && (
              <>
                <div className="menu-sep" />
                <button type="button" className="menu-item danger" role="menuitem" onClick={signOut}><LogOut size={16} /> Sign out</button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
