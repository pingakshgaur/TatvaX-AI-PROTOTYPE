import {
  BookOpen, Building2, ClipboardCheck, Languages, LayoutGrid, Library, Menu, MessageSquareText,
  ShieldCheck, TrendingUp,
} from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { useApp } from "../context/AppContext.jsx";
import { formatNumber } from "../lib/format.js";
import { stopSpeaking } from "../lib/voice.js";
import { AccountDialog, FeedbackDialog, TranslateDialog } from "./Dialogs.jsx";
import { Toasts } from "./ui.jsx";

const ShellContext = createContext(null);

export function useShell() {
  return useContext(ShellContext);
}

// Pages declare their breadcrumb trail: [{ label, to? }, ...]
export function useCrumbs(crumbs) {
  const { setCrumbs } = useShell();
  const key = JSON.stringify(crumbs);
  useEffect(() => { setCrumbs(JSON.parse(key)); }, [key, setCrumbs]);
}

function Sidebar({ open, onNavigate, onAccount }) {
  const { t, user, app, lang, setLang } = useApp();
  const location = useLocation();
  const learnActive = location.pathname.startsWith("/learn") || location.pathname === "/subjects";
  const link = (to, Icon, label, { end = false, active } = {}) => (
    <NavLink to={to} end={end} onClick={onNavigate}
      className={({ isActive }) => `nav-link${(active ?? isActive) ? " active" : ""}`}>
      <Icon size={17} strokeWidth={1.75} aria-hidden="true" />
      <span>{label}</span>
    </NavLink>
  );
  const registered = user && !user.is_guest;

  return (
    <aside className={`sidebar${open ? " open" : ""}`} aria-label="Primary">
      <Link to="/" className="sidebar-brand" onClick={onNavigate}>
        <span className="brand-mark" aria-hidden="true">त</span>
        <span className="brand-name">TatvaX</span>
        <span className="brand-version">v{app.version}</span>
      </Link>
      <nav className="sidebar-nav">
        <div className="nav-group">
          <span className="eyebrow">{t("group_learn")}</span>
          {link("/", LayoutGrid, t("nav_overview"), { end: true })}
          {link("/subjects", Library, t("nav_subjects"), { active: learnActive })}
          {link("/helpdesk", Building2, t("nav_helpdesk"))}
        </div>
        <div className="nav-group">
          <span className="eyebrow">{t("group_practice")}</span>
          {link("/assessments", ClipboardCheck, t("nav_quiz"))}
          {link("/notes", BookOpen, t("nav_library"))}
        </div>
        <div className="nav-group">
          <span className="eyebrow">{t("group_account")}</span>
          {link("/progress", TrendingUp, t("nav_progress"))}
        </div>
        {user?.role === "teacher" && (
          <div className="nav-group">
            <span className="eyebrow">{t("group_admin")}</span>
            {link("/teacher", ShieldCheck, t("nav_teacher"))}
          </div>
        )}
      </nav>
      <div className="sidebar-footer">
        <div>
          <label className="eyebrow" htmlFor="lang-select" style={{ display: "block", marginBottom: 6 }}>{t("language")}</label>
          <select id="lang-select" className="select" value={lang} onChange={(e) => setLang(e.target.value)}>
            {app.languages.map((l) => <option key={l.code} value={l.code}>{l.native}{l.code !== "en" ? ` (${l.name})` : ""}</option>)}
          </select>
        </div>
        <button type="button" className="user-card" onClick={onAccount}>
          <span className="avatar" aria-hidden="true">{registered ? user.name.trim().charAt(0).toUpperCase() : "G"}</span>
          <span className="user-meta">
            <strong>{registered ? user.name : t("guest")}</strong>
            <span>{user ? `${t("level")} ${user.level} · ${formatNumber(user.xp)} XP` : t("sign_in")}</span>
          </span>
        </button>
      </div>
    </aside>
  );
}

export default function Shell() {
  const { t, app, online } = useApp();
  const location = useLocation();
  const [crumbs, setCrumbsState] = useState([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [dialog, setDialog] = useState(null); // { name, tab }

  const setCrumbs = useCallback((next) => setCrumbsState(next), []);
  const openAccount = useCallback((tab) => setDialog({ name: "account", tab }), []);
  const openFeedback = useCallback(() => setDialog({ name: "feedback" }), []);
  const openTranslate = useCallback(() => setDialog({ name: "translate" }), []);
  const closeDialog = useCallback(() => setDialog(null), []);

  useEffect(() => {
    stopSpeaking();
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const onKey = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openTranslate();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [openTranslate]);

  const fullBleed = location.pathname.startsWith("/learn") || location.pathname.startsWith("/helpdesk");

  return (
    <ShellContext.Provider value={{ setCrumbs, openAccount, openFeedback, openTranslate }}>
      <a className="skip-link" href="#main">Skip to content</a>
      <div className="shell">
        <Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} onAccount={() => { setMenuOpen(false); openAccount(); }} />
        {menuOpen && <div className="scrim" onClick={() => setMenuOpen(false)} aria-hidden="true" />}
        <div className="main-column">
          <header className="topbar">
            <button className="icon-btn menu-button" type="button" aria-label="Open navigation" aria-expanded={menuOpen}
              onClick={() => setMenuOpen(true)}><Menu size={18} /></button>
            <nav className="breadcrumb" aria-label="Breadcrumb">
              <Link to="/">TatvaX</Link>
              {crumbs.map((crumb, i) => (
                <span key={i} style={{ display: "contents" }}>
                  <span aria-hidden="true">/</span>
                  {crumb.to && i < crumbs.length - 1
                    ? <Link to={crumb.to}>{crumb.label}</Link>
                    : <span className="current" aria-current={i === crumbs.length - 1 ? "page" : undefined}>{crumb.label}</span>}
                </span>
              ))}
            </nav>
            <div className="topbar-actions">
              <span className={`status-indicator${app.ai_enabled && online ? " online" : ""}`}
                title={app.ai_enabled ? `Model: ${app.ai_model}` : "Answers come from the study notes"}>
                <span className="dot" aria-hidden="true" />
                <span className="label">{app.ai_enabled ? t("ai_online") : t("ai_offline")}</span>
              </span>
              <button className="icon-btn bordered" type="button" onClick={openTranslate} aria-label={`${t("translate")} (Ctrl+K)`} title={`${t("translate")} (Ctrl+K)`}>
                <Languages size={16} />
              </button>
              <button className="icon-btn bordered" type="button" onClick={openFeedback} aria-label={t("feedback")} title={t("feedback")}>
                <MessageSquareText size={16} />
              </button>
            </div>
          </header>
          {!online && <div className="offline-bar" role="status">{t("offline")}</div>}
          <main id="main" tabIndex={-1} className={fullBleed ? "" : "page"}>
            <Outlet />
          </main>
        </div>
      </div>
      <AccountDialog open={dialog?.name === "account"} initialTab={dialog?.tab} onClose={closeDialog} />
      <FeedbackDialog open={dialog?.name === "feedback"} onClose={closeDialog} />
      <TranslateDialog open={dialog?.name === "translate"} onClose={closeDialog} />
      <Toasts />
    </ShellContext.Provider>
  );
}
