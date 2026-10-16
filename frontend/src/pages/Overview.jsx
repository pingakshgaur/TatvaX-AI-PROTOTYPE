import {
  ArrowRight, Award, BookOpen, ClipboardCheck, Flame, Languages, MessageSquareText, Sparkles, Star, Target,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import SubjectArt from "../components/SubjectArt.jsx";
import { CountUp } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { timeAgo } from "../lib/format.js";

function Title({ text, lang }) {
  // Highlight the second half of the English headline ("in your language").
  const split = lang === "en" ? text.split(", ") : [text];
  if (split.length !== 2) return <h1>{text}</h1>;
  return <h1>{split[0]}, <span className="accent">{split[1]}</span></h1>;
}

export default function Overview() {
  const { t, app, user, lang, progressVersion } = useApp();
  const navigate = useNavigate();
  const [progress, setProgress] = useState(null);
  const [recent, setRecent] = useState(null);
  const [question, setQuestion] = useState("");
  useCrumbs([{ label: t("nav_overview") }]);

  useEffect(() => {
    let live = true;
    api("/api/progress").then((res) => live && setProgress(res.progress)).catch(() => {});
    api("/api/conversations").then((res) => live && setRecent(res.conversations[0] || null)).catch(() => {});
    return () => { live = false; };
  }, [user?.id, progressVersion]);

  const ask = (event) => {
    event.preventDefault();
    if (question.trim()) navigate(`/learn/all?q=${encodeURIComponent(question.trim())}`);
  };

  const goal = progress?.goal ?? { done: 0, goal: user?.daily_goal ?? 5 };
  const earned = progress ? progress.badges.filter((b) => b.earned).length : 0;
  const recentSubject = recent && (recent.mode === "helpdesk" ? app.helpdesk : app.subjects.find((s) => s.slug === recent.subject));
  const recentHref = recent && (recent.mode === "helpdesk" ? `/tatvai/${recent.id}` : `/learn/${recent.subject || "all"}/${recent.id}`);

  return (
    <>
      <section className="hero">
        <div>
          <span className="eyebrow">{t("hero_eyebrow")}</span>
          <Title text={t("hero_title")} lang={lang} />
          <p className="lede">{t("hero_sub")}</p>
          <form className="command-bar" onSubmit={ask} role="search">
            <label className="sr-only" htmlFor="overview-ask">{t("hero_placeholder")}</label>
            <MessageSquareText size={18} className="muted" aria-hidden="true" />
            <input id="overview-ask" dir="auto" autoComplete="off" maxLength={2000}
              placeholder={t("hero_placeholder")} value={question} onChange={(e) => setQuestion(e.target.value)} />
            <button className="btn" type="submit" disabled={!question.trim()}>{t("ask")} <ArrowRight size={15} /></button>
          </form>
          <div className="language-ribbon" style={{ marginTop: 14 }}>
            {app.languages.map((l) => <span key={l.code} aria-current={l.code === lang}>{l.native}</span>)}
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <span className="shape s1" /><span className="shape s2" /><span className="shape s3" />
          <span className="shape s4" /><span className="shape s5" />
          <span className="glyph">त</span>
        </div>
      </section>

      <div className="quick-strip stagger">
        <Link to="/progress" className="quick-card lift" style={{ "--tone": "var(--c-leaf)", "--i": 0 }}>
          <span className="qc-icon"><Target size={18} /></span>
          <span className="qc-value"><CountUp value={Math.min(goal.done, goal.goal)} /><small className="muted" style={{ fontSize: 15 }}> / {goal.goal}</small></span>
          <span className="qc-label">{goal.done >= goal.goal ? "Daily goal complete. Great work!" : "Today's learning goal"}</span>
          <div className="goal-bar"><span style={{ width: `${Math.min(100, (goal.done / goal.goal) * 100)}%` }} /></div>
        </Link>
        <Link to="/progress" className="quick-card lift" style={{ "--tone": "var(--c-coral)", "--i": 1 }}>
          <span className="qc-icon"><Flame size={18} /></span>
          <span className="qc-value"><CountUp value={progress?.streak.current ?? 0} /></span>
          <span className="qc-label">{t("day_streak")} · {t("best_streak", { n: progress?.streak.best ?? 0 })}</span>
        </Link>
        <Link to="/progress" className="quick-card lift" style={{ "--tone": "var(--c-indigo)", "--i": 2 }}>
          <span className="qc-icon"><Star size={18} /></span>
          <span className="qc-value">{t("level")} <CountUp value={progress?.level ?? 1} /></span>
          <span className="qc-label"><CountUp value={progress?.xp ?? 0} /> XP · {t("xp_to_next", { n: (progress?.next_level_xp ?? 100) - (progress?.xp ?? 0), level: (progress?.level ?? 1) + 1 })}</span>
          <div className="xp-track" style={{ margin: "6px 0 0" }}><span style={{ width: `${Math.round((progress?.progress ?? 0) * 100)}%` }} /></div>
        </Link>
        <Link to="/progress#achievements" className="quick-card lift" style={{ "--tone": "var(--c-plum)", "--i": 3 }}>
          <span className="qc-icon"><Award size={18} /></span>
          <span className="qc-value"><CountUp value={earned} /><small className="muted" style={{ fontSize: 15 }}> / {progress?.badges.length ?? 13}</small></span>
          <span className="qc-label">{t("badges")} unlocked</span>
        </Link>
      </div>

      {recent && (
        <section className="section">
          <div className="section-head"><h2>Continue where you left off</h2></div>
          <Link to={recentHref} className="continue-card lift">
            <SubjectArt subject={recent.mode === "helpdesk" ? "tatvai" : recentSubject || "all"} size={42} />
            <span style={{ flex: 1, minWidth: 0 }}>
              <strong style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{recent.title}</strong>
              <span className="small muted">{recent.mode === "helpdesk" ? "TatvAI" : recentSubject?.title || t("all_subjects")} · {timeAgo(recent.updated_at)}</span>
            </span>
            <ArrowRight size={18} className="muted" />
          </Link>
        </section>
      )}

      <section className="section">
        <div className="section-head">
          <h2>{t("nav_subjects")}</h2>
          <Link className="small" to="/subjects">{t("choose_subject_sub")}</Link>
        </div>
        <div className="subject-tiles stagger">
          {app.subjects.map((s, i) => (
            <div key={s.slug} className="subject-tile lift" style={{ "--tone": s.color, "--i": i }}>
              <SubjectArt subject={s} variant="backdrop" />
              <SubjectArt subject={s} size={48} />
              <Link to={`/learn/${s.slug}`} style={{ color: "inherit", textDecoration: "none" }}>
                <h3>{s.title}</h3>
                <p>{s.description}</p>
              </Link>
              <div className="st-actions">
                <Link to={`/learn/${s.slug}`}>Learn</Link>
                <Link to={`/assessments/${s.slug}`}>Assess</Link>
                <Link to={`/notes/${s.slug}`}>Notes</Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head"><h2>More to explore</h2></div>
        <div className="quick-strip stagger">
          {[
            ["/tatvai", Sparkles, t("card_helpdesk"), t("card_helpdesk_desc"), "var(--c-plum)"],
            ["/assessments", ClipboardCheck, t("card_quiz"), t("card_quiz_desc"), "var(--c-coral)"],
            ["/notes", BookOpen, t("card_library"), t("card_library_desc"), "var(--c-saffron)"],
            ["/translate", Languages, t("nav_translate"), "Translate between 13 Indian languages as you type.", "var(--c-leaf)"],
          ].map(([to, Icon, title, desc, tone], i) => (
            <Link key={to} to={to} className="quick-card lift" style={{ "--tone": tone, "--i": i }}>
              <span className="qc-icon"><Icon size={18} /></span>
              <strong style={{ fontSize: 15.5 }}>{title}</strong>
              <span className="qc-label">{desc}</span>
            </Link>
          ))}
        </div>
      </section>

      <p className="small muted" style={{ marginTop: 32 }}>
        <span className="mono">TatvaX {app.version}</span>
        {" · "}
        {app.ai_enabled ? `AI: ${app.ai_model}${app.ai_provider ? ` via ${app.ai_provider}` : ""}` : "Notes mode: answers come from the school's study notes"}
        {" · "}
        <kbd>Ctrl</kbd> <kbd>K</kbd> {t("nav_translate")}
      </p>
    </>
  );
}
