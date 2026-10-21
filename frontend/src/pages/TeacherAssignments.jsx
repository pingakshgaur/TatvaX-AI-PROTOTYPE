// Teacher console, assignments: set an assessment or reading for a class and follow who has finished.
import { Archive, ArchiveRestore, BookOpen, ClipboardCheck, FileDown, Plus, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import SubjectArt from "../components/SubjectArt.jsx";
import { Dialog, EmptyState, InlineMarkdown, Loading, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { timeAgo } from "../lib/format.js";
import { dueLabel } from "./Assignments.jsx";

const KEYS = ["A", "B", "C", "D"];
const blank = { title: "", kind: "quiz", subjects: [], topic: "", instructions: "", grade: "", count: 10, difficulty: "medium", mode: "practice", due_date: "" };

function CreateForm({ onCreated, onCancel }) {
  const { app, lang, notify } = useApp();
  const [form, setForm] = useState({ ...blank, subjects: app.subjects.slice(0, 1).map((s) => s.slug) });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const toggle = (slug) => setForm((f) => ({ ...f, subjects: f.subjects.includes(slug) ? f.subjects.filter((s) => s !== slug) : [...f.subjects, slug] }));

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = { ...form, grade: form.grade ? Number(form.grade) : null, count: Number(form.count), language: lang, due_date: form.due_date || null };
      const { assignment } = await api("/api/admin/assignments", { method: "POST", body });
      notify(`Assignment set: ${assignment.title}`, { kind: "success" });
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel title="New assignment" actions={<button className="icon-btn" type="button" aria-label="Close" onClick={onCancel}><X size={16} /></button>}>
      <form onSubmit={submit} className="assign-form" noValidate>
        <div className="segmented" role="group" aria-label="Type" style={{ display: "flex" }}>
          <button type="button" style={{ flex: 1 }} aria-pressed={form.kind === "quiz"} onClick={() => setForm((f) => ({ ...f, kind: "quiz" }))}><ClipboardCheck size={14} /> Assessment</button>
          <button type="button" style={{ flex: 1 }} aria-pressed={form.kind === "reading"} onClick={() => setForm((f) => ({ ...f, kind: "reading" }))}><BookOpen size={14} /> Reading</button>
        </div>
        <div className="field"><label className="label" htmlFor="as-title">Title</label>
          <input className="input" id="as-title" maxLength={120} required value={form.title} onChange={set("title")}
            placeholder={form.kind === "quiz" ? "Fractions practice before the unit test" : "Read the chapter on the water cycle"} /></div>
        <div className="field"><span className="label">Subjects</span>
          <div className="subject-pick" role="group" aria-label="Subjects">
            {app.subjects.map((s) => (
              <button key={s.slug} type="button" aria-pressed={form.subjects.includes(s.slug)} onClick={() => toggle(s.slug)} style={{ "--tone": s.color }}>
                <SubjectArt subject={s} size={30} /> {s.title}
              </button>
            ))}
          </div></div>
        <div className="assign-grid">
          <div className="field"><label className="label" htmlFor="as-topic">{form.kind === "quiz" ? "Topic (optional)" : "Chapter or topic"}</label>
            <input className="input" id="as-topic" maxLength={80} value={form.topic} onChange={set("topic")} placeholder="e.g. Fractions" /></div>
          <div className="field"><label className="label" htmlFor="as-grade">Class</label>
            <select className="select" id="as-grade" value={form.grade} onChange={set("grade")}>
              <option value="">Every class</option>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => <option key={g} value={g}>Class {g}</option>)}
            </select></div>
          <div className="field"><label className="label" htmlFor="as-due">Due date</label>
            <input className="input" id="as-due" type="date" value={form.due_date} onChange={set("due_date")} /></div>
          {form.kind === "quiz" && (
            <>
              <div className="field"><label className="label" htmlFor="as-count">Questions</label>
                <input className="input" id="as-count" type="number" min={3} max={30} value={form.count} onChange={set("count")} /></div>
              <div className="field"><label className="label" htmlFor="as-diff">Difficulty</label>
                <select className="select" id="as-diff" value={form.difficulty} onChange={set("difficulty")}>
                  {["easy", "medium", "hard", "mixed"].map((d) => <option key={d} value={d}>{d[0].toUpperCase() + d.slice(1)}</option>)}
                </select></div>
              <div className="field"><label className="label" htmlFor="as-mode">Mode</label>
                <select className="select" id="as-mode" value={form.mode} onChange={set("mode")}>
                  <option value="practice">Practice (feedback after each question)</option>
                  <option value="exam">Exam (marked at the end)</option>
                  <option value="timed">Timed exam</option>
                </select></div>
            </>
          )}
        </div>
        <div className="field"><label className="label" htmlFor="as-notes">Instructions for students (optional)</label>
          <textarea className="textarea" id="as-notes" rows={2} maxLength={2000} value={form.instructions} onChange={set("instructions")} /></div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="dialog-footer">
          <button className="btn btn-secondary" type="button" onClick={onCancel}>Cancel</button>
          <button className="btn" type="submit" disabled={busy || !form.title.trim() || !form.subjects.length}>
            {busy ? <><span className="spinner" aria-hidden="true" /> {form.kind === "quiz" ? "Writing the questions…" : "Saving…"}</> : <><Plus size={15} /> Set assignment</>}
          </button>
        </div>
        {busy && form.kind === "quiz" && <p className="hint">Every student will answer the same questions, so they are written once now. This takes a few seconds.</p>}
      </form>
    </Panel>
  );
}

function Progress({ id, onClose }) {
  const [data, setData] = useState(null);
  useEffect(() => { api(`/api/admin/assignments/${id}`).then(setData).catch(() => onClose()); }, [id, onClose]);
  if (!data) return <Loading />;
  const { assignment: a, students } = data;
  const done = students.filter((s) => s.state === "done").length;
  return (
    <>
      <p className="small muted" style={{ marginTop: 0 }}>
        {a.subjects.map((s) => s.title).join(", ")} · {a.grade ? `Class ${a.grade}` : "Every class"}
        {a.due_date ? ` · due ${new Date(`${a.due_date}T00:00`).toLocaleDateString()}` : ""} · {done} of {students.length} finished
      </p>
      <table className="table">
        <thead><tr><th>Student</th><th>Class</th><th>Status</th>{a.kind === "quiz" && <th>Score (first try)</th>}<th>Finished</th><th /></tr></thead>
        <tbody>
          {students.map((s) => (
            <tr key={s.id}>
              <td>{s.name}</td>
              <td className="small muted">{s.grade ? `Class ${s.grade}` : "—"}</td>
              <td><span className={`tag ${s.state === "done" ? "positive" : s.state === "started" ? "accent" : ""}`}>{s.state === "done" ? "Finished" : s.state === "started" ? "Started" : "Not started"}</span></td>
              {a.kind === "quiz" && (
                <td className="num">
                  {s.total ? `${s.score}/${s.total} (${Math.round((100 * s.score) / s.total)}%)` : "—"}
                  {s.attempts > 1 && <span className="small muted"> · best {s.best_score}/{s.total} in {s.attempts} tries</span>}
                </td>
              )}
              <td className="small muted">{s.completed_at ? timeAgo(s.completed_at) : "—"}</td>
              <td><a className="icon-btn" href={`/print/student/${s.id}`} target="_blank" rel="noopener" title="Progress report" aria-label={`Progress report for ${s.name}`}><FileDown size={14} /></a></td>
            </tr>
          ))}
          {students.length === 0 && <tr><td colSpan={6} className="muted">No registered students in this class yet.</td></tr>}
        </tbody>
      </table>
      {a.preview?.length > 0 && (
        <details className="assign-preview">
          <summary>Questions ({a.preview.length})</summary>
          <ol>
            {a.preview.map((q, i) => (
              <li key={i}>
                <InlineMarkdown source={q.question} />
                <span className="small muted"> Answer: {KEYS[q.answer_index]}. <InlineMarkdown source={q.options[q.answer_index]} /></span>
              </li>
            ))}
          </ol>
        </details>
      )}
    </>
  );
}

export default function TeacherAssignments() {
  const { notify } = useApp();
  const [items, setItems] = useState(null);
  const [creating, setCreating] = useState(false);
  const [open, setOpen] = useState(null);
  const [confirm, setConfirm] = useState(null);

  const load = useCallback(() => api("/api/admin/assignments").then((res) => setItems(res.assignments)).catch(() => setItems([])), []);
  useEffect(() => { load(); }, [load]);
  const closeProgress = useCallback(() => setOpen(null), []);

  const patch = async (a, body, message) => {
    try {
      await api(`/api/admin/assignments/${a.id}`, { method: "PATCH", body });
      notify(message);
      load();
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };
  const remove = async (a) => {
    setConfirm(null);
    try {
      await api(`/api/admin/assignments/${a.id}`, { method: "DELETE" });
      load();
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };

  if (!items) return <Loading />;
  return (
    <>
      {creating ? <CreateForm onCreated={() => { setCreating(false); load(); }} onCancel={() => setCreating(false)} /> : (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, gap: 12, flexWrap: "wrap" }}>
          <p className="small muted" style={{ margin: 0 }}>Set an assessment or reading for a class. Students see it under Assignments.</p>
          <button className="btn" type="button" onClick={() => setCreating(true)}><Plus size={15} /> New assignment</button>
        </div>
      )}
      {items.length === 0 && !creating ? (
        <EmptyState icon={ClipboardCheck} title="No assignments yet">Create one to give a class the same assessment or reading.</EmptyState>
      ) : (
        <div className="assignment-list" style={{ marginTop: 14 }}>
          {items.map((a) => {
            const share = a.students ? a.done / a.students : 0;
            const due = dueLabel(a.due_date);
            return (
              <article key={a.id} className={`assignment-card teacher${a.archived ? " done" : ""}`} style={{ "--tone": a.subjects[0]?.color || "var(--c-teal)" }}>
                <SubjectArt subject={a.subjects[0]} size={44} />
                <div className="ac-body">
                  <span className="eyebrow">{a.kind === "quiz" ? `Assessment · ${a.questions} questions · ${a.mode}` : "Reading"} · {a.grade ? `Class ${a.grade}` : "Every class"}{a.archived ? " · Archived" : ""}</span>
                  <strong>{a.title}</strong>
                  <span className="ac-meta">
                    {due && <span className={`due ${due.state}`}>{due.text}</span>}
                    <span>{a.done}/{a.students} finished{a.started ? ` · ${a.started} started` : ""}</span>
                    {a.average != null && <span className="ac-score">Average {a.average}%</span>}
                  </span>
                  <span className="ac-progress" aria-hidden="true"><span style={{ width: `${share * 100}%` }} /></span>
                </div>
                <div className="ac-buttons">
                  <button className="btn btn-secondary btn-sm" type="button" onClick={() => setOpen(a)}>Progress</button>
                  <button className="icon-btn" type="button" title={a.archived ? "Restore" : "Archive"} aria-label={a.archived ? "Restore" : "Archive"}
                    onClick={() => patch(a, { archived: !a.archived }, a.archived ? "Assignment restored" : "Assignment archived; students no longer see it")}>
                    {a.archived ? <ArchiveRestore size={15} /> : <Archive size={15} />}
                  </button>
                  <button className="icon-btn" type="button" title="Delete" aria-label="Delete" onClick={() => setConfirm(a)}><Trash2 size={15} /></button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <Dialog open={Boolean(open)} onClose={closeProgress} title={open?.title || ""} wide>
        {open && <Progress id={open.id} onClose={closeProgress} />}
      </Dialog>
      <Dialog open={Boolean(confirm)} onClose={() => setConfirm(null)} title="Delete assignment">
        <p>Delete “{confirm?.title}”? Students' results are kept in their history, but the assignment disappears. Archiving hides it instead.</p>
        <div className="dialog-footer">
          <button className="btn btn-secondary" type="button" onClick={() => setConfirm(null)}>Cancel</button>
          <button className="btn btn-danger" type="button" onClick={() => remove(confirm)}><Trash2 size={15} /> Delete</button>
        </div>
      </Dialog>
    </>
  );
}
