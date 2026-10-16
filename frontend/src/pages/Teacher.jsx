import {
  BarChart3, ClipboardList, Cpu, Eye, FileDown, FilePenLine, Lock, MessageSquareText, PenLine, Plus, Save, Trash2, Users,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { BarList, ColumnChart } from "../components/Charts.jsx";
import { useCrumbs, useShell } from "../components/Shell.jsx";
import { Dialog, EmptyState, Loading, Markdown, PageHeader, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import AISettings from "./AISettings.jsx";
import TeacherAssignments from "./TeacherAssignments.jsx";
import { api } from "../lib/api.js";
import { formatNumber, shortDate, timeAgo } from "../lib/format.js";

const TABS = [
  ["overview", BarChart3, "overview"],
  ["students", Users, "students"],
  ["assignments", ClipboardList, "nav_assignments"],
  ["content", FilePenLine, "content"],
  ["feedback", MessageSquareText, "feedback"],
  ["ai", Cpu, "ai_settings"],
];

function useLoad(path, deps = []) {
  const [state, setState] = useState({ data: null, error: "" });
  const reload = useCallback(() => {
    setState({ data: null, error: "" });
    api(path).then((data) => setState({ data, error: "" })).catch((err) => setState({ data: null, error: err.message }));
  }, [path]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { reload(); }, [reload, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps
  return { ...state, reload };
}

function Overview() {
  const { languageInfo } = useApp();
  const { data, error } = useLoad("/api/admin/overview");
  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <Loading />;
  const c = data.counts;
  const listOrEmpty = (items, props) => (items.length ? <BarList items={items} {...props} /> : <p className="muted">No data yet.</p>);

  return (
    <>
      <div className="kpi-strip">
        <div className="kpi"><span className="eyebrow">Registered students</span><span className="value">{formatNumber(c.students)}</span>
          <span className="meta">{formatNumber(c.guests)} guest learners</span></div>
        <div className="kpi"><span className="eyebrow">Active learners</span><span className="value">{formatNumber(c.active_week)}</span>
          <span className="meta">Last 7 days</span></div>
        <div className="kpi"><span className="eyebrow">Questions this week</span><span className="value">{formatNumber(c.questions_week)}</span>
          <span className="meta">{formatNumber(c.questions)} all time</span></div>
        <div className="kpi"><span className="eyebrow">Assessment average</span><span className="value">{c.quizzes ? `${c.quiz_average}%` : "—"}</span>
          <span className="meta">{formatNumber(c.quizzes)} completed</span></div>
      </div>
      <div className="grid grid-2 section">
        <Panel title="Questions per day">
          <p className="hint" style={{ marginTop: -4 }}>Last 14 days, all learners</p>
          <ColumnChart caption="Questions per day" valueName="Questions"
            items={data.questions_per_day.map((d) => ({ label: shortDate(d.day), value: d.value }))} />
        </Panel>
        <Panel title="Questions by subject">
          {listOrEmpty(data.by_subject, { caption: "Questions by subject", valueName: "Questions" })}
        </Panel>
        <Panel title="Languages in use">
          {listOrEmpty(data.by_language.map((d) => ({ label: languageInfo(d.label).name, value: d.value })),
            { caption: "Questions by language", valueName: "Questions" })}
        </Panel>
        <Panel title="Assessment average by subject">
          <p className="hint" style={{ marginTop: -4 }}>Lowest first. These topics may need revision in class.</p>
          {listOrEmpty(data.quiz_scores.map((d) => ({
            label: d.label, value: d.average, display: `${d.average}%`, title: `${d.label}: ${d.average}% across ${d.quizzes} assessments`,
          })), { caption: "Assessment average", valueName: "Average %", max: 100 })}
        </Panel>
      </div>
    </>
  );
}

function Students() {
  const { data, error } = useLoad("/api/admin/students");
  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <Loading />;
  if (!data.students.length) {
    return <Panel><EmptyState icon={Users} title="No registered students yet">Students appear here after they create an account.</EmptyState></Panel>;
  }
  return (
    <Panel tight>
      <div className="table-wrap">
        <table className="table">
          <thead><tr>
            <th>Student</th><th className="num">Class</th><th className="num">Level</th><th className="num">XP</th>
            <th className="num">Questions</th><th className="num">Assessments</th><th className="num">Average</th><th>Last active</th><th><span className="sr-only">Report</span></th>
          </tr></thead>
          <tbody>{data.students.map((s) => (
            <tr key={s.id}>
              <td><strong>{s.name}</strong><div className="small muted">{s.email}</div></td>
              <td className="num">{s.grade ?? "—"}</td>
              <td className="num">{s.level}</td>
              <td className="num">{formatNumber(s.xp)}</td>
              <td className="num">{formatNumber(s.questions)}</td>
              <td className="num">{formatNumber(s.quizzes)}</td>
              <td className="num">{s.quiz_average != null ? `${s.quiz_average}%` : "—"}</td>
              <td className="small muted">{s.last_active ? timeAgo(`${s.last_active}T12:00:00Z`) : "—"}</td>
              <td><a className="btn btn-ghost btn-sm" href={`/print/student/${s.id}`} target="_blank" rel="noopener"
                title="Progress report as a PDF, for parents or records"><FileDown size={14} /> Report</a></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </Panel>
  );
}

function ContentEditor({ selected }) {
  const { reloadApp, notify } = useApp();
  const navigate = useNavigate();
  const library = useLoad("/api/library");
  const isNew = selected === "new";
  const slug = isNew ? null : selected || library.data?.documents[0]?.slug;
  const [doc, setDoc] = useState(null);
  const [form, setForm] = useState(null);
  const [preview, setPreview] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    setError("");
    setPreview(false);
    if (isNew) {
      setDoc(null);
      setForm({ title: "", description: "", icon: "book-open", color: "#0f5a57", kind: "subject", body: "## Chapter 1: \n\n**Topic**\nWrite the explanation here.\n" });
      return;
    }
    if (!slug) return;
    setForm(null);
    api(`/api/admin/documents/${encodeURIComponent(slug)}`)
      .then(({ document }) => { setDoc(document); setForm(document); })
      .catch((err) => setError(err.message));
  }, [slug, isNew]);

  const update = (field) => (event) => setForm((f) => ({ ...f, [field]: event.target.value }));

  const save = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    const body = { title: form.title, description: form.description, icon: form.icon, color: form.color, body: form.body };
    try {
      const res = isNew
        ? await api("/api/admin/documents", { method: "POST", body: { ...body, kind: form.kind } })
        : await api(`/api/admin/documents/${encodeURIComponent(slug)}`, { method: "PUT", body });
      await reloadApp();
      library.reload();
      notify("Notes saved", { detail: "The tutor uses them from the next question.", kind: "success" });
      if (isNew) navigate(`/teacher/content/${res.document.slug}`);
      else { setDoc(res.document); setForm(res.document); }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setConfirmDelete(false);
    try {
      await api(`/api/admin/documents/${encodeURIComponent(slug)}`, { method: "DELETE" });
      await reloadApp();
      library.reload();
      notify("Notes deleted");
      navigate("/teacher/content");
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };

  if (!library.data) return <Loading />;

  return (
    <div className="editor-layout">
      <Panel tight title="Documents">
        <div className="doc-nav">
          {library.data.documents.map((d) => (
            <Link key={d.slug} to={`/teacher/content/${d.slug}`} className={d.slug === slug ? "active" : ""}>
              <span className="swatch" style={{ background: d.color }} />
              <span style={{ flex: 1 }}>{d.title}</span>
              {d.kind === "helpdesk" && <span className="tag">TatvAI info</span>}
            </Link>
          ))}
          <Link to="/teacher/content/new" className={isNew ? "active" : ""}><Plus size={15} /> New subject</Link>
        </div>
      </Panel>

      {!form ? (error ? <p className="form-error">{error}</p> : <Loading />) : (
        <Panel title={isNew ? "New document" : form.title}
          actions={doc && <span className="small muted">Updated {timeAgo(doc.updated_at)}</span>}>
          <form onSubmit={save} noValidate>
            <div className="grid grid-2" style={{ gap: "0 16px" }}>
              <div className="field"><label className="label" htmlFor="doc-title">Title</label>
                <input className="input" id="doc-title" maxLength={80} required value={form.title} onChange={update("title")} /></div>
              <div className="field"><label className="label" htmlFor="doc-description">Short description</label>
                <input className="input" id="doc-description" maxLength={200} value={form.description} onChange={update("description")} /></div>
              <div className="field"><label className="label" htmlFor="doc-icon">Icon name</label>
                <input className="input" id="doc-icon" maxLength={40} value={form.icon} onChange={update("icon")} />
                <span className="hint">A Lucide icon name, for example <code>book-open</code>.</span></div>
              <div className="field"><label className="label" htmlFor="doc-color">Accent colour</label>
                <input className="input" id="doc-color" type="color" value={form.color} onChange={update("color")} style={{ padding: 4, height: 38 }} /></div>
            </div>
            {isNew && (
              <div className="field"><label className="label" htmlFor="doc-kind">Type</label>
                <select className="select" id="doc-kind" value={form.kind} onChange={update("kind")}>
                  <option value="subject">Subject notes</option>
                  <option value="helpdesk">School information for TatvAI</option>
                </select></div>
            )}
            <div className="field">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label className="label" htmlFor="doc-body">Notes (Markdown)</label>
                <div className="segmented" role="group" aria-label="Editor mode">
                  <button type="button" aria-pressed={!preview} onClick={() => setPreview(false)}><PenLine size={14} /> Write</button>
                  <button type="button" aria-pressed={preview} onClick={() => setPreview(true)}><Eye size={14} /> Preview</button>
                </div>
              </div>
              {preview
                ? <div className="panel" style={{ minHeight: 460 }}><div className="panel-body"><Markdown source={form.body} /></div></div>
                : <textarea className="textarea code-editor" id="doc-body" value={form.body} onChange={update("body")} spellCheck />}
              <span className="hint">Use <code>## Chapter</code> headings and <code>**Topic**</code> lines. The AI tutor answers from these notes
                {(doc?.kind || form.kind) === "helpdesk" ? " and never invents school details that aren't written here." : "."}</span>
            </div>
            <p className="form-error" role="alert">{error}</p>
            <div className="dialog-footer" style={{ justifyContent: "space-between" }}>
              {doc ? <button className="btn btn-danger" type="button" onClick={() => setConfirmDelete(true)}><Trash2 size={15} /> Delete</button> : <span />}
              <button className="btn" type="submit" disabled={busy}><Save size={15} /> Save</button>
            </div>
          </form>
        </Panel>
      )}

      <Dialog open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete document">
        <p>Delete “{doc?.title}”? Students will no longer see these notes and the tutor will stop using them.</p>
        <div className="dialog-footer">
          <button className="btn btn-secondary" type="button" onClick={() => setConfirmDelete(false)}>Cancel</button>
          <button className="btn btn-danger" type="button" onClick={remove}><Trash2 size={15} /> Delete</button>
        </div>
      </Dialog>
    </div>
  );
}

function Feedback() {
  const { data, error } = useLoad("/api/admin/feedback");
  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <Loading />;
  if (!data.feedback.length) return <Panel><EmptyState icon={MessageSquareText} title="No feedback yet" /></Panel>;
  return (
    <Panel tight>
      {data.feedback.map((f) => (
        <div key={f.id} className="list-row" style={{ alignItems: "flex-start" }}>
          <span className="tag" style={{ minWidth: 48, justifyContent: "center" }}>{f.rating ? `${f.rating} / 5` : "n/a"}</span>
          <div className="grow">
            <p dir="auto" style={{ whiteSpace: "pre-wrap", margin: 0 }}>{f.message}</p>
            <div className="desc">{f.name || "Anonymous"} · {timeAgo(f.created_at)}{f.page ? ` · ${f.page}` : ""}</div>
          </div>
        </div>
      ))}
    </Panel>
  );
}

export default function TeacherConsole() {
  const { t, user, app } = useApp();
  const { openAccount } = useShell();
  const params = useParams();
  const tab = TABS.some(([name]) => name === params.tab) ? params.tab : "overview";
  const tabLabel = TABS.find(([name]) => name === tab)[2];
  useCrumbs([{ label: t("nav_teacher"), to: "/teacher" }, { label: t(tabLabel) }]);
  // On narrow screens the tab row scrolls; keep the open tab visible.
  useEffect(() => {
    document.querySelector(".tabs .active")?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [tab]);

  if (!user || user.is_guest || user.role !== "teacher") {
    return (
      <Panel>
        <EmptyState icon={Lock} title="Teacher access required"
          action={<button className="btn" type="button" onClick={() => openAccount("login")}>{t("sign_in")}</button>}>
          Sign in with a teacher account to view class analytics and edit the study notes.
        </EmptyState>
      </Panel>
    );
  }

  return (
    <>
      <PageHeader eyebrow={t("group_admin")} title={t("teacher_title")}
        lede={app.ai_enabled
          ? `AI tutor: ${app.ai_model} via ${app.ai_provider}`
          : <>The AI tutor is off, so students receive answers from the study notes. <Link to="/teacher/ai">Connect an AI provider</Link> (NVIDIA, Gemini and Groq have free tiers) to turn it on.</>} />
      <nav className="tabs" aria-label={t("teacher_title")}>
        {TABS.map(([name, Icon, label]) => (
          <Link key={name} to={`/teacher/${name}`} className={name === tab ? "active" : ""} aria-current={name === tab ? "page" : undefined}>
            <Icon size={15} /> {t(label)}
          </Link>
        ))}
      </nav>
      {tab === "overview" && <Overview />}
      {tab === "students" && <Students />}
      {tab === "assignments" && <TeacherAssignments />}
      {tab === "content" && <ContentEditor selected={params.slug} />}
      {tab === "feedback" && <Feedback />}
      {tab === "ai" && <AISettings />}
    </>
  );
}
