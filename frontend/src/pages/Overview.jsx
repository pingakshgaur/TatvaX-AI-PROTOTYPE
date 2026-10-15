import { ArrowRight, BookOpen, Building2, ClipboardCheck, GraduationCap } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import { Meter, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { formatNumber } from "../lib/format.js";
import { SubjectRows } from "./Subjects.jsx";

export default function Overview() {
  const { t, app, user, lang } = useApp();
  const navigate = useNavigate();
  const [progress, setProgress] = useState(null);
  const [question, setQuestion] = useState("");
  useCrumbs([{ label: t("nav_overview") }]);

  useEffect(() => {
    let live = true;
    api("/api/progress").then((res) => live && setProgress(res.progress)).catch(() => {});
    return () => { live = false; };
  }, [user?.id]);

  const ask = (event) => {
    event.preventDefault();
    if (question.trim()) navigate(`/learn/all?q=${encodeURIComponent(question.trim())}`);
  };

  const modules = [
    ["/subjects", GraduationCap, t("card_learn"), t("card_learn_desc")],
    ["/helpdesk", Building2, t("card_helpdesk"), t("card_helpdesk_desc")],
    ["/assessments", ClipboardCheck, t("card_quiz"), t("card_quiz_desc")],
    ["/notes", BookOpen, t("card_library"), t("card_library_desc")],
  ];

  return (
    <>
      <section className="overview-intro">
        <div>
          <span className="eyebrow">{t("hero_eyebrow")}</span>
          <h1>{t("hero_title")}</h1>
          <p className="lede">{t("hero_sub")}</p>
          <form className="command-bar" onSubmit={ask} role="search">
            <label className="sr-only" htmlFor="overview-ask">{t("hero_placeholder")}</label>
            <input id="overview-ask" dir="auto" autoComplete="off" maxLength={2000}
              placeholder={t("hero_placeholder")} value={question} onChange={(e) => setQuestion(e.target.value)} />
            <button className="btn" type="submit" disabled={!question.trim()}>{t("ask")} <ArrowRight size={15} /></button>
          </form>
        </div>
        <div>
          <span className="eyebrow" style={{ display: "block", marginBottom: 10 }}>13 languages</span>
          <div className="language-ribbon">
            {app.languages.map((l) => <span key={l.code} aria-current={l.code === lang}>{l.native}</span>)}
          </div>
        </div>
      </section>

      <div className="kpi-strip">
        <div className="kpi">
          <span className="eyebrow">{t("level")}</span>
          <span className="value">{progress?.level ?? 1}</span>
          <Meter value={progress?.progress ?? 0} label={t("level")} />
          <span className="meta">{t("xp_to_next", { n: formatNumber((progress?.next_level_xp ?? 100) - (progress?.xp ?? 0)), level: (progress?.level ?? 1) + 1 })}</span>
        </div>
        <div className="kpi">
          <span className="eyebrow">{t("xp")}</span>
          <span className="value">{formatNumber(progress?.xp ?? 0)}</span>
          <span className="meta">Earned from questions and assessments</span>
        </div>
        <div className="kpi">
          <span className="eyebrow">{t("day_streak")}</span>
          <span className="value">{progress?.streak.current ?? 0}</span>
          <span className="meta">{t("best_streak", { n: progress?.streak.best ?? 0 })}</span>
        </div>
        <div className="kpi">
          <span className="eyebrow">{t("badges")}</span>
          <span className="value">{progress ? progress.badges.filter((b) => b.earned).length : 0}<small> / {progress?.badges.length ?? 10}</small></span>
          <span className="meta"><Link to="/progress">{t("nav_progress")}</Link></span>
        </div>
      </div>

      <section className="section">
        <div className="section-head"><h2>Workspace</h2></div>
        <div className="module-grid">
          {modules.map(([to, Icon, title, desc]) => (
            <Link key={to} to={to} className="module">
              <Icon className="module-icon" size={22} strokeWidth={1.6} aria-hidden="true" />
              <h3>{title}</h3>
              <p>{desc}</p>
              <span className="module-foot">{t("open")} <ArrowRight size={14} /></span>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>{t("nav_subjects")}</h2>
          <Link className="small" to="/subjects">{t("choose_subject_sub")}</Link>
        </div>
        <Panel tight><SubjectRows showAll={false} /></Panel>
      </section>

      <p className="small muted" style={{ marginTop: 32 }}>
        <span className="mono">TatvaX {app.version}</span>
        {" · "}
        {app.ai_enabled ? `AI tutor: ${app.ai_model} on NVIDIA` : "Notes mode: answers come from the school's study notes"}
        {" · "}
        <kbd>Ctrl</kbd> <kbd>K</kbd> {t("translate")}
      </p>
    </>
  );
}
