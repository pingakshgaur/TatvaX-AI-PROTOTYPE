// Work set by teachers: assessments the whole class takes, and reading from the study notes.
import { BookOpen, CalendarDays, CheckCircle2, ClipboardCheck, Eye, Play, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useCrumbs, useShell } from "../components/Shell.jsx";
import SubjectArt from "../components/SubjectArt.jsx";
import { EmptyState, Loading, PageHeader } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { daysFromToday } from "../lib/format.js";

const FILTERS = [["todo", "To do"], ["done", "Finished"], ["all", "All"]];

export function dueLabel(due) {
  if (!due) return null;
  const days = daysFromToday(due);
  if (days < 0) return { text: `${-days} day${days === -1 ? "" : "s"} overdue`, state: "overdue" };
  if (days === 0) return { text: "Due today", state: "today" };
  if (days === 1) return { text: "Due tomorrow", state: "soon" };
  return { text: `Due ${new Date(`${due}T00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" })}`, state: "later" };
}

export default function Assignments() {
  const { t, user, notify } = useApp();
  const { openAccount } = useShell();
  const navigate = useNavigate();
  const [items, setItems] = useState(null);
  const [filter, setFilter] = useState("todo");
  const [busy, setBusy] = useState(null);
  useCrumbs([{ label: t("nav_assignments") }]);
  const registered = user && !user.is_guest;

  useEffect(() => {
    if (!registered) { setItems([]); return; }
    api("/api/assignments").then((res) => setItems(res.assignments)).catch(() => setItems([]));
  }, [registered, user?.id]);

  const start = async (a) => {
    setBusy(a.id);
    try {
      const { quiz } = await api(`/api/assignments/${a.id}/start`, { method: "POST", body: {} });
      navigate("/assessments", { state: { quiz } });
    } catch (err) {
      notify(err.message, { kind: "error" });
      setBusy(null);
    }
  };

  const toggleRead = async (a) => {
    const done = a.status.state !== "done";
    try {
      const { status } = await api(`/api/assignments/${a.id}/done`, { method: "POST", body: { done } });
      setItems((list) => list.map((x) => (x.id === a.id ? { ...x, status, overdue: false } : x)));
      if (done) notify(`Finished: ${a.title}`, { kind: "success" });
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };

  if (!registered) {
    return (
      <>
        <PageHeader eyebrow={t("group_learn")} title={t("nav_assignments")} lede="Work your teacher sets for your class appears here." />
        <EmptyState title="Sign in to see your assignments"
          action={<button className="btn" type="button" onClick={() => openAccount("register")}><UserPlus size={15} /> Create a free account</button>}>
          Assignments are set for classes, so they need an account. Add your class in Settings so you see the right work.
        </EmptyState>
      </>
    );
  }
  if (!items) return <Loading />;

  const shown = items.filter((a) => (filter === "all" ? true : filter === "done" ? a.status.state === "done" : a.status.state !== "done"));
  const open = items.filter((a) => a.status.state !== "done").length;

  return (
    <>
      <PageHeader eyebrow={t("group_learn")} title={t("nav_assignments")}
        lede={open ? `${open} piece${open === 1 ? "" : "s"} of work to finish.` : "You're up to date with your class work."} />
      {!user.grade && (
        <p className="notice-line">Add your class in <button type="button" className="link-btn" onClick={() => openAccount("settings")}>Settings</button> to see work set for your class.</p>
      )}
      <div className="segmented" role="group" aria-label="Show" style={{ marginBottom: 16 }}>
        {FILTERS.map(([id, label]) => (
          <button key={id} type="button" aria-pressed={filter === id} onClick={() => setFilter(id)}>
            {label} {id === "todo" && open ? `(${open})` : ""}
          </button>
        ))}
      </div>

      {shown.length === 0 ? (
        <EmptyState icon={CheckCircle2} title={items.length ? "Nothing here" : "No assignments yet"}>
          {items.length ? "Try another filter." : "When your teacher sets work for your class, it will appear here."}
        </EmptyState>
      ) : (
        <div className="assignment-list stagger">
          {shown.map((a, i) => {
            const due = a.status.state !== "done" ? dueLabel(a.due_date) : null;
            const main = a.subjects[0];
            const done = a.status.state === "done";
            return (
              <article key={a.id} className={`assignment-card${done ? " done" : ""}`} style={{ "--tone": main?.color || "var(--c-teal)", "--i": Math.min(i, 8) }}>
                <SubjectArt subject={main} size={48} />
                <div className="ac-body">
                  <span className="eyebrow">
                    {a.kind === "quiz" ? <><ClipboardCheck size={12} /> Assessment · {a.questions} questions · {a.mode}</> : <><BookOpen size={12} /> Reading</>}
                  </span>
                  <strong>{a.title}</strong>
                  {a.instructions && <p>{a.instructions}</p>}
                  <span className="ac-meta">
                    {a.subjects.map((s) => s.title).join(", ")}{a.topic ? ` · ${a.topic}` : ""}
                    {due && <span className={`due ${due.state}`}><CalendarDays size={12} /> {due.text}</span>}
                    {done && a.status.total != null && (
                      <span className="ac-score">Score {a.status.score}/{a.status.total}
                        {a.status.attempts > 1 ? ` · best ${a.status.best_score}/${a.status.total}` : ""}</span>
                    )}
                    {done && a.kind === "reading" && <span className="ac-score">Finished</span>}
                  </span>
                </div>
                <div className="ac-buttons">
                  {a.kind === "quiz" ? (
                    <>
                      {done && <Link className="btn btn-secondary btn-sm" to={`/assessments/review/${a.status.quiz_id}`}><Eye size={14} /> {t("review_btn")}</Link>}
                      <button className={`btn btn-sm${done ? " btn-ghost" : ""}`} type="button" disabled={busy === a.id} onClick={() => start(a)}>
                        {busy === a.id ? <span className="spinner" aria-hidden="true" /> : <Play size={14} />} {done ? "Try again" : a.status.state === "started" ? "Continue" : "Start"}
                      </button>
                    </>
                  ) : (
                    <>
                      {a.subjects.map((s) => (
                        <Link key={s.slug} className="btn btn-secondary btn-sm"
                          to={`/notes/${s.slug}${a.topic ? `?h=${encodeURIComponent(a.topic)}` : ""}`}><BookOpen size={14} /> Open notes</Link>
                      ))}
                      <button className={`btn btn-sm${done ? " btn-ghost" : ""}`} type="button" onClick={() => toggleRead(a)}>
                        <CheckCircle2 size={14} /> {done ? "Mark as not done" : "Mark as done"}
                      </button>
                    </>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </>
  );
}
