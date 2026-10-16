// The student's avatar in the top bar: level ring and streak, opening a short menu with
// their level, today's goal, a glance at their to-do list, settings, progress and sign-out.
import { ArrowRight, BarChart3, Check, Flame, ListChecks, LogIn, LogOut, Plus, Settings, UserPlus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { formatNumber } from "../lib/format.js";

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

export default function ProfileMenu({ onAccount }) {
  const { user, setUser, notify, t, progressVersion } = useApp();
  const [open, setOpen] = useState(false);
  const [stats, setStats] = useState(null);
  const [todos, setTodos] = useState(null);
  const [quick, setQuick] = useState("");
  const ref = useRef(null);
  const location = useLocation();
  const registered = user && !user.is_guest;
  const initial = registered ? user.name.trim().charAt(0).toUpperCase() : "G";

  useEffect(() => {
    let live = true;
    api("/api/progress").then((res) => live && setStats(res.progress)).catch(() => {});
    return () => { live = false; };
  }, [user?.id, progressVersion, open]);

  useEffect(() => {
    if (!open) return undefined;
    let live = true;
    api("/api/todos").then((res) => live && setTodos(res.todos)).catch(() => live && setTodos([]));
    return () => { live = false; };
  }, [open, user?.id]);

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

  const signOut = async () => {
    await api("/api/auth/logout", { method: "POST", body: {} });
    setUser(null);
    setOpen(false);
    notify("Signed out");
  };

  // Ticked tasks stay in the panel, struck through, until the menu is opened again.
  const toggleTodo = async (todo) => {
    setTodos((list) => list.map((x) => (x.id === todo.id ? { ...x, done: !x.done, touched: true } : x)));
    try {
      await api(`/api/todos/${todo.id}`, { method: "PATCH", body: { done: !todo.done } });
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };

  const addQuick = async (event) => {
    event.preventDefault();
    if (!quick.trim()) return;
    try {
      const { todo } = await api("/api/todos", { method: "POST", body: { title: quick.trim() } });
      setTodos((list) => [todo, ...(list || [])]);
      setQuick("");
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };

  const level = stats?.level ?? user?.level ?? 1;
  const xp = stats?.xp ?? user?.xp ?? 0;
  const progress = stats?.progress ?? user?.progress ?? 0;
  const streak = stats?.streak.current ?? 0;
  const goal = stats?.goal ?? { done: 0, goal: user?.daily_goal ?? 5 };
  const listed = (todos || []).filter((x) => !x.done || x.touched);
  const openCount = (todos || []).filter((x) => !x.done).length;
  const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  const close = () => setOpen(false);

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
                <span className="sub">
                  {t("level")} {level}{user?.grade ? ` · Class ${user.grade}` : ""}{user?.role === "teacher" ? " · Teacher" : ""}
                  {streak > 0 ? ` · ${streak} day streak` : ""}
                </span>
              </div>
            </div>
            <div className="xp-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)} aria-label="XP to next level">
              <span style={{ width: `${Math.round(progress * 100)}%` }} />
            </div>
            <span className="sub pm-line">
              <span>{formatNumber(xp)} XP · {formatNumber((stats?.next_level_xp ?? 100) - xp)} to level {level + 1}</span>
              <span className={goal.done >= goal.goal ? "goal-done" : ""}>Daily goal {Math.min(goal.done, goal.goal)}/{goal.goal}</span>
            </span>
          </div>

          <section className="pm-todos" aria-label="To-do list">
            <div className="pm-todos-head">
              <span className="eyebrow"><ListChecks size={13} /> {t("nav_todos")}</span>
              <span className="small muted">{todos ? `${openCount} open` : ""}</span>
            </div>
            {todos === null ? <span className="spinner" aria-label="Loading" /> : (
              <ul>
                {listed.slice(0, 4).map((todo) => (
                  <li key={todo.id}>
                    <button type="button" className="check sm" role="checkbox" aria-checked={todo.done}
                      aria-label={`Mark ${todo.title} as ${todo.done ? "not done" : "done"}`} onClick={() => toggleTodo(todo)}>
                      {todo.done && <Check size={11} />}
                    </button>
                    <span className={todo.done ? "struck" : ""}>{todo.title}</span>
                    {todo.due_date && !todo.done && (
                      <span className={`due ${todo.due_date < today ? "overdue" : todo.due_date === today ? "today" : ""}`}>
                        {todo.due_date === today ? "Today" : new Date(`${todo.due_date}T00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" })}
                      </span>
                    )}
                  </li>
                ))}
                {listed.length === 0 && <li className="small muted">Nothing on your list. Add a task below.</li>}
              </ul>
            )}
            <form className="pm-quick" onSubmit={addQuick}>
              <label className="sr-only" htmlFor="pm-quick">Quick task</label>
              <input id="pm-quick" value={quick} maxLength={200} placeholder="Quick add a task" onChange={(e) => setQuick(e.target.value)} />
              <button type="submit" className="icon-btn" aria-label="Add task" disabled={!quick.trim()}><Plus size={15} /></button>
            </form>
            <Link to="/todos" className="pm-open" role="menuitem" onClick={close}>
              {t("open_todos")}{todos && todos.length ? ` (${todos.length})` : ""} <ArrowRight size={14} />
            </Link>
          </section>

          <div className="menu-list">
            {!registered && (
              <>
                <button type="button" className="menu-item" role="menuitem" onClick={() => { close(); onAccount("register"); }}>
                  <span className="mi-icon" style={{ background: "var(--c-teal)" }}><UserPlus size={16} /></span> Create a free account
                  <span className="mi-meta">Save progress</span>
                </button>
                <button type="button" className="menu-item" role="menuitem" onClick={() => { close(); onAccount("login"); }}>
                  <span className="mi-icon" style={{ background: "var(--c-indigo)" }}><LogIn size={16} /></span> Sign in
                </button>
              </>
            )}
            <button type="button" className="menu-item" role="menuitem" onClick={() => { close(); onAccount("settings"); }}>
              <span className="mi-icon" style={{ background: "var(--c-plum)" }}><Settings size={16} /></span> {t("settings")}
              <span className="mi-meta">Language, theme, goal</span>
            </button>
            <Link to="/progress" className="menu-item" role="menuitem">
              <span className="mi-icon" style={{ background: "var(--c-saffron)" }}><BarChart3 size={16} /></span> {t("my_progress")}
              <span className="mi-meta">Badges, leaderboard</span>
            </Link>
            {registered && (
              <>
                <div className="menu-sep" />
                <button type="button" className="menu-item danger" role="menuitem" onClick={signOut}><LogOut size={16} /> {t("sign_out")}</button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
