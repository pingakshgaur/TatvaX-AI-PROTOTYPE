import {
  BarChart3, CheckCircle2, Copy, Cpu, ExternalLink, Eye, EyeOff, FilePenLine, KeyRound, Lock, MessageSquareText, PenLine, Plus, Save,
  Trash2, Users, XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { BarList, ColumnChart } from "../components/Charts.jsx";
import { useCrumbs, useShell } from "../components/Shell.jsx";
import { Dialog, EmptyState, Loading, Markdown, PageHeader, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { formatNumber, shortDate, timeAgo } from "../lib/format.js";

const TABS = [
  ["overview", BarChart3, "overview"],
  ["students", Users, "students"],
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
            <th className="num">Questions</th><th className="num">Assessments</th><th className="num">Average</th><th>Last active</th>
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
              {d.kind === "helpdesk" && <span className="tag">Help desk</span>}
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
                  <option value="helpdesk">Help desk information</option>
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

function AISettings() {
  const { reloadApp, notify } = useApp();
  const [state, setState] = useState(null);
  const [key, setKey] = useState("");
  const [model, setModel] = useState("");
  const [customModel, setCustomModel] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [testResult, setTestResult] = useState(null);
  const [revealed, setRevealed] = useState(null);

  const reveal = async () => {
    if (revealed) { setRevealed(null); return; }
    try {
      setRevealed((await api("/api/admin/ai/key")).api_key);
    } catch (err) {
      setError(err.message);
    }
  };
  const copyKey = async () => {
    const key = revealed || (await api("/api/admin/ai/key")).api_key;
    await navigator.clipboard.writeText(key);
    notify("API key copied");
  };

  const apply = useCallback((data) => {
    setState(data);
    const known = data.models.some((m) => m.id === data.ai.model);
    setModel(known ? data.ai.model : "custom");
    setCustomModel(known ? "" : data.ai.model);
  }, []);

  useEffect(() => {
    api("/api/admin/ai").then(apply).catch((err) => setError(err.message));
  }, [apply]);

  const test = async () => {
    setError("");
    setBusy("test");
    try {
      const result = await api("/api/admin/ai/test", { method: "POST", body: {} });
      setTestResult({ ok: true, text: `Connected in ${(result.latency_ms / 1000).toFixed(1)} s. The model replied: “${result.reply}”` });
      setState((current) => ({ ...current, ai: result.ai }));
      await reloadApp();
    } catch (err) {
      setTestResult({ ok: false, text: err.message });
      api("/api/admin/ai").then(apply).catch(() => {});
      reloadApp().catch(() => {});
    } finally {
      setBusy("");
    }
  };

  const save = async (body, message) => {
    setError("");
    setTestResult(null);
    setBusy("save");
    try {
      const data = await api("/api/admin/ai", { method: "PUT", body });
      apply(data);
      setKey("");
      setRevealed(null);
      await reloadApp();
      notify(message, { kind: "success" });
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setBusy("");
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    const body = { model: model === "custom" ? customModel.trim() : model };
    const newKey = key.trim();
    if (newKey) body.api_key = newKey;
    const saved = await save(body, newKey ? "NVIDIA API key saved" : "AI settings saved");
    if (saved?.ai.configured && newKey) test(); // check a new key straight away
  };

  if (error && !state) return <p className="form-error">{error}</p>;
  if (!state) return <Loading />;
  const { ai, models } = state;
  const [statusKind, statusLabel] = !ai.allowed ? ["negative", "Turned off on the server"]
    : !ai.configured ? ["", "Not configured"]
    : ai.available ? ["positive", "Active"]
    : ["negative", "Key rejected"];
  const selected = models.find((m) => m.id === model);

  return (
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))", alignItems: "start" }}>
      <Panel title="NVIDIA AI tutor" actions={<span className={`tag ${statusKind}`}>{statusLabel}</span>}>
        {ai.configured && (
          <div className="key-card" style={ai.available ? undefined : { background: "var(--negative-tint)", borderColor: "var(--negative)" }}>
            <span className="key-icon" style={ai.available ? undefined : { background: "var(--negative)" }}><KeyRound size={17} /></span>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div className="kc-meta">{ai.source === "environment" ? "Key from the server's NVIDIA_API_KEY setting" : "Saved key"}
                {ai.saved_at && ai.source === "settings" ? ` · saved ${timeAgo(ai.saved_at)}` : ""}</div>
              <code>{revealed || `${ai.key_hint?.split("…")[0] ?? ""}${"•".repeat(24)}${ai.key_hint?.split("…")[1] ?? ""}`}</code>
            </div>
            <button className="icon-btn" type="button" onClick={reveal} aria-label={revealed ? "Hide key" : "Show key"} title={revealed ? "Hide key" : "Show key"}>
              {revealed ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
            <button className="icon-btn" type="button" onClick={() => copyKey().catch((err) => setError(err.message))} aria-label="Copy key" title="Copy key">
              <Copy size={16} />
            </button>
          </div>
        )}
        <form onSubmit={submit} noValidate>
          <div className="field">
            <label className="label" htmlFor="nv-key">{ai.configured ? "Replace the key" : "NVIDIA API key"}</label>
            <input className="input mono" id="nv-key" type="password" autoComplete="off" spellCheck={false}
              placeholder={ai.key_hint ? `Saved: ${ai.key_hint} (enter a new key to replace it)` : "nvapi-..."}
              value={key} onChange={(e) => setKey(e.target.value)} />
            <span className="hint">
              {ai.source === "environment"
                ? "Currently using the key from the server's NVIDIA_API_KEY setting. A key saved here takes priority."
                : "Stored only on this server. It is never shown again or sent to students' browsers."}
            </span>
          </div>
          <div className="field">
            <label className="label" htmlFor="nv-model">Model</label>
            <select className="select" id="nv-model" value={model} onChange={(e) => setModel(e.target.value)}>
              {models.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
              <option value="custom">Another model from build.nvidia.com…</option>
            </select>
            {selected && <span className="hint">{selected.note}</span>}
            {model === "custom" && (
              <input className="input mono" style={{ marginTop: 8 }} aria-label="Model ID" placeholder="publisher/model-name"
                value={customModel} onChange={(e) => setCustomModel(e.target.value)} />
            )}
          </div>
          {ai.last_error && !testResult && <p className="form-error">{ai.last_error}</p>}
          {error && <p className="form-error" role="alert">{error}</p>}
          {testResult && (
            <p className="small" role="status"
              style={{ display: "flex", gap: 8, alignItems: "flex-start", color: testResult.ok ? "var(--positive)" : "var(--negative)" }}>
              {testResult.ok ? <CheckCircle2 size={16} /> : <XCircle size={16} />} <span>{testResult.text}</span>
            </p>
          )}
          <div className="dialog-footer" style={{ justifyContent: "space-between", flexWrap: "wrap" }}>
            {ai.source === "settings"
              ? <button className="btn btn-danger" type="button" disabled={Boolean(busy)}
                  onClick={() => save({ api_key: "" }, "NVIDIA API key removed")}><Trash2 size={15} /> Remove key</button>
              : <span />}
            <span style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-secondary" type="button" onClick={test} disabled={!ai.configured || Boolean(busy)}>
                {busy === "test" ? <span className="spinner" aria-hidden="true" /> : <CheckCircle2 size={15} />} Test connection
              </button>
              <button className="btn" type="submit" disabled={Boolean(busy)}><Save size={15} /> Save</button>
            </span>
          </div>
        </form>
      </Panel>

      <Panel title="Get a free NVIDIA API key">
        <ol className="prose small" style={{ paddingLeft: "1.2em", marginTop: 0 }}>
          <li>Go to <a href="https://build.nvidia.com" target="_blank" rel="noopener noreferrer">build.nvidia.com <ExternalLink size={12} /></a> and
            sign in, or create a free NVIDIA account.</li>
          <li>Open your profile menu, choose <strong>API Keys</strong>, then <strong>Generate API Key</strong>.</li>
          <li>Copy the key (it starts with <code>nvapi-</code>), paste it here and select <strong>Save</strong>.</li>
        </ol>
        <p className="small muted" style={{ marginBottom: 8 }}>
          <KeyRound size={13} style={{ verticalAlign: "-2px" }} /> NVIDIA's free developer tier is meant for prototyping and limits
          how many requests you can make (about 40 a minute). When the limit is reached, students automatically get answers from
          the study notes until it resets, so nothing breaks.
        </p>
        <p className="small muted" style={{ margin: 0 }}>
          Without a key, TatvaX still works in notes mode: answers, assessments and translation all run without AI.
        </p>
      </Panel>
    </div>
  );
}

export default function TeacherConsole() {
  const { t, user, app } = useApp();
  const { openAccount } = useShell();
  const params = useParams();
  const tab = TABS.some(([name]) => name === params.tab) ? params.tab : "overview";
  const tabLabel = TABS.find(([name]) => name === tab)[2];
  useCrumbs([{ label: t("nav_teacher"), to: "/teacher" }, { label: t(tabLabel) }]);

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
          ? `AI tutor: ${app.ai_model} on NVIDIA`
          : <>The AI tutor is off, so students receive answers from the study notes. <Link to="/teacher/ai">Add a free NVIDIA API key</Link> to turn it on.</>} />
      <nav className="tabs" aria-label={t("teacher_title")}>
        {TABS.map(([name, Icon, label]) => (
          <Link key={name} to={`/teacher/${name}`} className={name === tab ? "active" : ""} aria-current={name === tab ? "page" : undefined}>
            <Icon size={15} /> {t(label)}
          </Link>
        ))}
      </nav>
      {tab === "overview" && <Overview />}
      {tab === "students" && <Students />}
      {tab === "content" && <ContentEditor selected={params.slug} />}
      {tab === "feedback" && <Feedback />}
      {tab === "ai" && <AISettings />}
    </>
  );
}
