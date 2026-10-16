import { ArrowRight, BookOpen, ChevronRight, ClipboardCheck, FileDown, MessageSquareText } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import SubjectArt from "../components/SubjectArt.jsx";
import { CountUp } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { timeAgo } from "../lib/format.js";

function chaptersRead(slug) {
  try { return JSON.parse(localStorage.getItem(`tatvax.read.${slug}`) || "[]").length; } catch { return 0; }
}

// Compact subject list, used where a short picker is needed.
export function SubjectRows({ showAll = true }) {
  const { app, t } = useApp();
  return (
    <>
      {showAll && (
        <Link className="list-row" to="/learn/all">
          <SubjectArt subject="all" size={42} />
          <span className="grow">
            <span className="title">{t("all_subjects")}</span>
            <span className="desc" style={{ display: "block" }}>{t("all_subjects_desc")}</span>
          </span>
          <ChevronRight className="chev" size={18} aria-hidden="true" />
        </Link>
      )}
      {app.subjects.map((subject) => (
        <Link className="list-row" key={subject.slug} to={`/learn/${subject.slug}`}>
          <SubjectArt subject={subject} size={42} />
          <span className="grow">
            <span className="title">{subject.title}</span>
            <span className="desc" style={{ display: "block" }}>{subject.description}</span>
          </span>
          <ChevronRight className="chev" size={18} aria-hidden="true" />
        </Link>
      ))}
    </>
  );
}

function SubjectCard({ subject, stats, index }) {
  const { t } = useApp();
  const read = Math.min(chaptersRead(subject.slug), stats?.chapters || 0);
  const readShare = stats?.chapters ? read / stats.chapters : 0;
  return (
    <article className="atlas-card lift" style={{ "--tone": subject.color, "--i": index }}>
      <SubjectArt subject={subject} variant="backdrop" />
      <header className="ac-head">
        <SubjectArt subject={subject} size={58} />
        <div>
          <span className="eyebrow">{stats?.last_active ? `Last studied ${timeAgo(stats.last_active)}` : "Not started yet"}</span>
          <h2>{subject.title}</h2>
        </div>
      </header>
      <p className="ac-desc">{subject.description}</p>

      <div className="ac-stats">
        <div><b><CountUp value={stats?.chapters ?? 0} /></b><span>Chapters</span></div>
        <div><b><CountUp value={stats?.topics ?? 0} /></b><span>Topics</span></div>
        <div><b><CountUp value={stats?.questions ?? 0} /></b><span>Questions asked</span></div>
        <div><b>{stats?.average != null ? <><CountUp value={stats.average} />%</> : "—"}</b><span>{stats?.quizzes ? `${stats.quizzes} assessment${stats.quizzes === 1 ? "" : "s"}` : "Avg. score"}</span></div>
      </div>

      <div className="ac-meter">
        <div className="row"><span>Notes read</span><span>{read} of {stats?.chapters ?? 0} chapters</span></div>
        <div className="bar" role="progressbar" aria-label={`${subject.title} notes read`} aria-valuemin={0} aria-valuemax={100}
          aria-valuenow={Math.round(readShare * 100)}><span style={{ width: `${readShare * 100}%` }} /></div>
      </div>

      {stats?.chapter_titles?.length > 0 && (
        <div className="ac-topics" aria-label="Chapters">
          {stats.chapter_titles.slice(0, 5).map((title) => (
            <Link key={title} to={`/notes/${subject.slug}?h=${encodeURIComponent(title)}`}>{title}</Link>
          ))}
          {stats.chapter_titles.length > 5 && <Link to={`/notes/${subject.slug}`}>+{stats.chapters - 5} more</Link>}
        </div>
      )}

      <div className="ac-actions">
        <Link className="btn btn-tone" to={`/learn/${subject.slug}`}><MessageSquareText size={15} /> {t("open")} tutor</Link>
        <Link className="btn btn-secondary" to={`/assessments/${subject.slug}`}><ClipboardCheck size={15} /> {t("nav_quiz")}</Link>
        <Link className="btn btn-ghost" to={`/notes/${subject.slug}`}><BookOpen size={15} /> Notes</Link>
        <a className="icon-btn bordered" href={`/print/notes/${subject.slug}`} target="_blank" rel="noopener"
          title="Export notes as PDF" aria-label={`Export ${subject.title} notes as PDF`}><FileDown size={15} /></a>
      </div>
    </article>
  );
}

export default function Subjects() {
  const { t, app, user, progressVersion } = useApp();
  const [overview, setOverview] = useState({});
  useCrumbs([{ label: t("nav_subjects") }]);

  useEffect(() => {
    let live = true;
    api("/api/subjects/overview")
      .then((res) => live && setOverview(Object.fromEntries(res.subjects.map((s) => [s.slug, s]))))
      .catch(() => {});
    return () => { live = false; };
  }, [user?.id, progressVersion]);

  const all = Object.values(overview);
  const totals = {
    chapters: all.reduce((n, s) => n + s.chapters, 0),
    topics: all.reduce((n, s) => n + s.topics, 0),
    questions: all.reduce((n, s) => n + s.questions, 0),
  };

  return (
    <>
      <section className="atlas-hero">
        <div>
          <span className="eyebrow">{t("group_learn")}</span>
          <h1>{t("choose_subject")}</h1>
          <p className="lede">{t("choose_subject_sub")}</p>
        </div>
        <div className="atlas-totals" aria-label="Library at a glance">
          <div><b><CountUp value={app.subjects.length} /></b><span>Subjects</span></div>
          <div><b><CountUp value={totals.chapters} /></b><span>Chapters</span></div>
          <div><b><CountUp value={totals.topics} /></b><span>Topics</span></div>
          <div><b><CountUp value={totals.questions} /></b><span>Your questions</span></div>
        </div>
      </section>

      <div className="atlas-grid stagger">
        {app.subjects.map((subject, i) => <SubjectCard key={subject.slug} subject={subject} stats={overview[subject.slug]} index={i} />)}
      </div>

      <div className="atlas-side stagger">
        <Link to="/learn/all" className="atlas-card compact lift" style={{ "--tone": "var(--c-indigo)", "--i": 0 }}>
          <SubjectArt subject="all" variant="backdrop" />
          <SubjectArt subject="all" size={50} />
          <span className="grow">
            <strong>{t("all_subjects")}</strong>
            <span className="small">{t("all_subjects_desc")}</span>
          </span>
          <ArrowRight size={18} className="muted" />
        </Link>
        <Link to="/tatvai" className="atlas-card compact lift" style={{ "--tone": "var(--c-plum)", "--i": 1 }}>
          <SubjectArt subject="tatvai" variant="backdrop" />
          <SubjectArt subject="tatvai" size={50} />
          <span className="grow">
            <strong>TatvAI</strong>
            <span className="small">{t("card_helpdesk_desc")}</span>
          </span>
          <ArrowRight size={18} className="muted" />
        </Link>
      </div>
    </>
  );
}
