import {
  BookOpen, ClipboardCheck, Languages, LayoutGrid, Library, ListChecks, Menu, ShieldCheck, Sparkles,
} from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useApp } from "../context/AppContext.jsx";
import { stopSpeaking } from "../lib/voice.js";
import Celebration from "./Celebration.jsx";
import { AccountDialog, FeedbackDialog } from "./Dialogs.jsx";
import ProfileMenu from "./ProfileMenu.jsx";
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

function Sidebar({ open, onNavigate }) {
  const { t, user, app } = useApp();
  const location = useLocation();
  const learnActive = location.pathname.startsWith("/learn") || location.pathname === "/subjects";
  const link = (to, Icon, label, color, { end = false, active } = {}) => (
    <NavLink to={to} end={end} onClick={onNavigate} style={{ "--nav-color": color }}
      className={({ isActive }) => `nav-link${(active ?? isActive) ? " active" : ""}`}>
      <Icon size={17} strokeWidth={1.75} aria-hidden="true" />
      <span>{label}</span>
    </NavLink>
  );

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
          {link("/", LayoutGrid, t("nav_overview"), "var(--c-teal)", { end: true })}
          {link("/subjects", Library, t("nav_subjects"), "var(--c-indigo)", { active: learnActive })}
          {link("/tatvai", Sparkles, t("nav_helpdesk"), "var(--c-plum)")}
        </div>
        <div className="nav-group">
          <span className="eyebrow">{t("group_practice")}</span>
          {link("/assessments", ClipboardCheck, t("nav_quiz"), "var(--c-coral)")}
          {link("/notes", BookOpen, t("nav_library"), "var(--c-saffron)")}
          {link("/translate", Languages, t("nav_translate"), "var(--c-leaf)")}
          {link("/todos", ListChecks, "To-do list", "var(--c-indigo)")}
        </div>
        {user?.role === "teacher" && (
          <div className="nav-group">
            <span className="eyebrow">{t("group_admin")}</span>
            {link("/teacher", ShieldCheck, t("nav_teacher"), "var(--c-teal)")}
          </div>
        )}
      </nav>
    </aside>
  );
}

export default function Shell() {
  const { t, app, online } = useApp();
  const location = useLocation();
  const navigate = useNavigate();
  const [crumbs, setCrumbsState] = useState([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [dialog, setDialog] = useState(null); // { name, tab }

  const setCrumbs = useCallback((next) => setCrumbsState(next), []);
  const openAccount = useCallback((tab) => setDialog({ name: "account", tab }), []);
  const openFeedback = useCallback(() => setDialog({ name: "feedback" }), []);
  const closeDialog = useCallback(() => setDialog(null), []);

  useEffect(() => {
    stopSpeaking();
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const onKey = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        navigate("/translate");
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [navigate]);

  const fullBleed = location.pathname.startsWith("/learn") || location.pathname.startsWith("/tatvai");

  return (
    <ShellContext.Provider value={{ setCrumbs, openAccount, openFeedback }}>
      <a className="skip-link" href="#main">Skip to content</a>
      <div className="shell">
        <Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} />
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
              <ProfileMenu onAccount={openAccount} />
            </div>
          </header>
          {!online && <div className="offline-bar" role="status">{t("offline")}</div>}
          <main id="main" tabIndex={-1} className={fullBleed ? "" : "page"}>
            <div className={fullBleed ? "" : "page-enter"} key={fullBleed ? "chat" : location.pathname}>
              <Outlet />
            </div>
          </main>
        </div>
      </div>
      <AccountDialog open={dialog?.name === "account"} initialTab={dialog?.tab} onClose={closeDialog} onFeedback={openFeedback} />
      <FeedbackDialog open={dialog?.name === "feedback"} onClose={closeDialog} />
      <Toasts />
      <Celebration />
    </ShellContext.Provider>
  );
}
