import { ArrowLeft, Clock, Eye, FileDown, Play, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import SubjectArt from "../components/SubjectArt.jsx";
import { CountUp, Dialog, EmptyState, Loading, PageHeader } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { timeAgo } from "../lib/format.js";
import { formatTime, Results } from "./Assessments.jsx";

const FILTERS = [["all", "All"], ["finished", "Finished"], ["unfinished", "Not finished"]];

function title(quiz) {
  const subjects = quiz.subjects.map((s) => s.title).join(" + ");
  return quiz.topic ? `${subjects}: ${quiz.topic}` : subjects;
}

function scoreTone(percent) {
  if (percent >= 80) return "var(--c-leaf)";
  if (percent >= 50) return "var(--c-saffron)";
  return "var(--c-coral)";
}

// Start the same questions again, reshuffled, and open them on the assessments page.
function useRetake() {
  const navigate = useNavigate();
  const { notify } = useApp();
  return async (id) => {
    try {
      const { quiz } = await api(`/api/quiz/${id}/retake`, { method: "POST", body: {} });
      navigate("/assessments", { state: { quiz } });
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };
}

export function AssessmentHistory() {
  const { t, app, user, notify } = useApp();
  const [quizzes, setQuizzes] = useState(null);
  const [filter, setFilter] = useState("all");
  const [subject, setSubject] = useState("all");
  const [query, setQuery] = useState("");
  const [pendingDelete, setPendingDelete] = useState(null);
  const retake = useRetake();
  useCrumbs([{ label: t("nav_quiz"), to: "/assessments" }, { label: "History" }]);

  useEffect(() => {
    api("/api/quizzes").then((res) => setQuizzes(res.quizzes)).catch(() => setQuizzes([]));
  }, [user?.id]);

  const shown = useMemo(() => (quizzes || []).filter((q) => {
    if (filter === "finished" && !q.completed_at) return false;
    if (filter === "unfinished" && q.completed_at) return false;
    if (subject !== "all" && !q.subjects.some((s) => s.slug === subject)) return false;
    return !query.trim() || title(q).toLowerCase().includes(query.trim().toLowerCase());
  }), [quizzes, filter, subject, query]);

  const finished = (quizzes || []).filter((q) => q.completed_at && q.total);
  const average = finished.length ? Math.round(finished.reduce((n, q) => n + (100 * q.score) / q.total, 0) / finished.length) : 0;
  const best = finished.length ? Math.max(...finished.map((q) => Math.round((100 * q.score) / q.total))) : 0;
  const questions = finished.reduce((n, q) => n + q.total, 0);

  const remove = async () => {
    const quiz = pendingDelete;
    setPendingDelete(null);
    try {
      await api(`/api/quiz/${quiz.id}`, { method: "DELETE" });
      setQuizzes((list) => list.filter((q) => q.id !== quiz.id));
      notify("Assessment removed from your history");
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };

  return (
    <>
      <PageHeader eyebrow={t("nav_quiz")} title="My assessments"
        lede="Every assessment you have taken. Review your answers, retake a test or export it as a PDF report."
        actions={<Link className="btn" to="/assessments"><Plus size={15} /> New assessment</Link>} />

      <div className="quick-strip stagger" style={{ marginBottom: 22 }}>
        {[
          ["Assessments taken", finished.length, "", "var(--c-indigo)"],
          ["Average score", average, "%", "var(--c-teal)"],
          ["Best score", best, "%", "var(--c-leaf)"],
          ["Questions answered", questions, "", "var(--c-coral)"],
        ].map(([label, value, unit, tone], i) => (
          <div key={label} className="quick-card" style={{ "--tone": tone, "--i": i }}>
            <span className="qc-value"><CountUp value={value} />{unit}</span>
            <span className="qc-label">{label}</span>
          </div>
        ))}
      </div>

      <div className="history-toolbar">
        <div className="segmented" role="group" aria-label="Show">
          {FILTERS.map(([id, label]) => <button key={id} type="button" aria-pressed={filter === id} onClick={() => setFilter(id)}>{label}</button>)}
        </div>
        <select className="select" aria-label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} style={{ width: "auto" }}>
          <option value="all">All subjects</option>
          {app.subjects.map((s) => <option key={s.slug} value={s.slug}>{s.title}</option>)}
        </select>
        <label className="history-search">
          <Search size={15} aria-hidden="true" />
          <span className="sr-only">Search assessments</span>
          <input type="search" placeholder="Search by subject or topic" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
      </div>

      {!quizzes ? <Loading /> : shown.length === 0 ? (
        <EmptyState title={quizzes.length ? "No assessments match" : "No assessments yet"}
          action={<Link className="btn" to="/assessments"><Play size={15} /> Take your first assessment</Link>}>
          {quizzes.length ? "Try a different filter." : "Assessments you take will be saved here so you can revisit them."}
        </EmptyState>
      ) : (
        <div className="history-list stagger">
          {shown.map((q, i) => {
            const percent = q.completed_at && q.total ? Math.round((100 * q.score) / q.total) : null;
            const main = q.subjects[0];
            return (
              <article key={q.id} className="history-card" style={{ "--tone": main?.color || "var(--c-teal)", "--i": Math.min(i, 8) }}>
                <div className="hc-art">
                  {q.subjects.slice(0, 3).map((s) => <SubjectArt key={s.slug} subject={s} size={q.subjects.length > 1 ? 34 : 46} />)}
                </div>
                <div className="hc-main">
                  <strong>{title(q)}</strong>
                  <span className="hc-meta">
                    <span className="tag" style={{ textTransform: "capitalize" }}>{q.mode}</span>
                    <span style={{ textTransform: "capitalize" }}>{q.difficulty}</span>
                    <span>{q.total} questions</span>
                    {q.duration_s != null && <span><Clock size={12} /> {formatTime(q.duration_s)}</span>}
                    <span title={new Date(q.created_at).toLocaleString()}>{timeAgo(q.completed_at || q.created_at)}</span>
                  </span>
                </div>
                {percent != null ? (
                  <div className="hc-score" style={{ "--score": scoreTone(percent) }}>
                    <b>{percent}%</b><span>{q.score}/{q.total}</span>
                  </div>
                ) : (
                  <div className="hc-score pending"><b>{q.answered}/{q.total}</b><span>answered</span></div>
                )}
                <div className="hc-actions">
                  {q.completed_at && <Link className="btn btn-sm btn-secondary" to={`/assessments/review/${q.id}`}><Eye size={14} /> Review</Link>}
                  <button className="btn btn-sm" type="button" onClick={() => retake(q.id)}><Play size={14} /> Retake</button>
                  <a className="icon-btn bordered" href={`/print/assessment/${q.id}`} target="_blank" rel="noopener"
                    title="Export PDF" aria-label={`Export ${title(q)} as PDF`}><FileDown size={15} /></a>
                  <button className="icon-btn bordered" type="button" title="Delete" aria-label={`Delete ${title(q)}`}
                    onClick={() => setPendingDelete(q)}><Trash2 size={15} /></button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <Dialog open={Boolean(pendingDelete)} onClose={() => setPendingDelete(null)} title="Delete assessment">
        <p>Remove “{pendingDelete && title(pendingDelete)}” from your history? Your XP and badges stay.</p>
        <div className="dialog-footer">
          <button className="btn btn-secondary" type="button" onClick={() => setPendingDelete(null)}>{t("cancel")}</button>
          <button className="btn btn-danger" type="button" onClick={remove}><Trash2 size={15} /> {t("delete")}</button>
        </div>
      </Dialog>
    </>
  );
}

export function AssessmentReview() {
  const { t } = useApp();
  const { id } = useParams();
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState(null);
  const [error, setError] = useState("");
  const retake = useRetake();
  useCrumbs([{ label: t("nav_quiz"), to: "/assessments" }, { label: "History", to: "/assessments/history" }, { label: quiz?.subject_title || "Review" }]);

  useEffect(() => {
    setQuiz(null);
    api(`/api/quiz/${id}`).then((res) => setQuiz(res.quiz)).catch((err) => setError(err.message));
  }, [id]);

  if (error) return <EmptyState title="Assessment not found" action={<Link className="btn" to="/assessments/history">Back to history</Link>}>{error}</EmptyState>;
  if (!quiz) return <Loading />;
  if (!quiz.finished) {
    return (
      <EmptyState title="This assessment wasn't finished" action={<button className="btn" type="button" onClick={() => retake(quiz.id)}><Play size={15} /> Retake it</button>}>
        Only finished assessments can be reviewed.
      </EmptyState>
    );
  }
  return (
    <>
      <Link className="btn btn-ghost btn-sm" to="/assessments/history" style={{ marginBottom: 12 }}><ArrowLeft size={14} /> All assessments</Link>
      <Results review quiz={quiz} outcome={{ finished: quiz.finished, answers: [] }}
        onRestart={() => retake(quiz.id)} onRetry={(next) => navigate("/assessments", { state: { quiz: next } })} />
    </>
  );
}
