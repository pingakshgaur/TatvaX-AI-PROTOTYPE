import {
  ArrowDownUp, CalendarDays, Check, CheckCheck, ChevronDown, Copy, ExternalLink, Flag, GripVertical, ListChecks, Plus, RotateCcw,
  Search, SquareCheck, Tag, Trash2, X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Link } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import SubjectArt from "../components/SubjectArt.jsx";
import { CountUp, Dialog, EmptyState, Loading } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { daysFromToday, schoolToday } from "../lib/format.js";
import useUndoableDelete from "../lib/useUndoableDelete.js";

const PRIORITIES = [
  ["urgent", "Urgent", "var(--c-coral)"],
  ["high", "High", "var(--c-saffron)"],
  ["medium", "Medium", "var(--c-indigo)"],
  ["low", "Low", "var(--c-teal)"],
];
const PRIORITY = Object.fromEntries(PRIORITIES.map(([id, label, tone], rank) => [id, { label, tone, rank }]));
const VIEWS = ["all", "active", "today", "upcoming", "overdue", "done"];
const todoPath = (id) => `/api/todos/${id}`;
const SORTS = [["manual", "My order"], ["due", "Due date"], ["priority", "Priority"], ["newest", "Newest"]];

const todayIso = () => schoolToday();
const addDays = (n) => schoolToday(n);

function dueLabel(due) {
  if (!due) return null;
  const today = todayIso();
  if (due === today) return { text: "Today", state: "today" };
  if (due === addDays(1)) return { text: "Tomorrow", state: "soon" };
  if (due < today) {
    const days = -daysFromToday(due);
    return { text: days === 1 ? "Yesterday" : `${days} days overdue`, state: "overdue" };
  }
  return { text: new Date(`${due}T00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" }), state: "later" };
}

function TagInput({ tags, onChange }) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const value = draft.trim().replace(/,$/, "");
    if (value && !tags.includes(value) && tags.length < 8) onChange([...tags, value.slice(0, 24)]);
    setDraft("");
  };
  return (
    <div className="tag-input">
      {tags.map((tag) => (
        <span key={tag} className="todo-tag">#{tag}
          <button type="button" aria-label={`Remove tag ${tag}`} onClick={() => onChange(tags.filter((t) => t !== tag))}><X size={11} /></button>
        </span>
      ))}
      {tags.length < 8 && (
        <input value={draft} placeholder={tags.length ? "Add tag" : "Add tags, e.g. exam, homework"} aria-label="Add a tag"
          onChange={(e) => setDraft(e.target.value)} onBlur={add}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(); }
            if (e.key === "Backspace" && !draft && tags.length) onChange(tags.slice(0, -1));
          }} />
      )}
    </div>
  );
}

function TodoEditor({ todo, onUpdate }) {
  const { app } = useApp();
  const [title, setTitle] = useState(todo.title);
  const [notes, setNotes] = useState(todo.notes || "");
  const [subtask, setSubtask] = useState("");

  useEffect(() => { setTitle(todo.title); setNotes(todo.notes || ""); }, [todo.id, todo.title, todo.notes]);

  const subtasks = todo.subtasks || [];
  const setSubtasks = (next) => onUpdate({ subtasks: next });
  const addSubtask = () => {
    if (!subtask.trim() || subtasks.length >= 30) return;
    setSubtasks([...subtasks, { text: subtask.trim(), done: false }]);
    setSubtask("");
  };

  return (
    <div className="todo-editor">
      <label className="te-field wide">
        <span>Title</span>
        <input className="input" value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)}
          onBlur={() => title.trim() && title !== todo.title && onUpdate({ title: title.trim() })}
          onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()} />
      </label>
      <label className="te-field wide">
        <span>Notes</span>
        <textarea className="input" rows={3} value={notes} maxLength={4000} placeholder="Details, page numbers, links…"
          onChange={(e) => setNotes(e.target.value)} onBlur={() => notes !== (todo.notes || "") && onUpdate({ notes })} />
      </label>
      <div className="te-field">
        <span>Priority</span>
        <div className="priority-pick" role="radiogroup" aria-label="Priority">
          {PRIORITIES.map(([id, label, tone]) => (
            <button key={id} type="button" role="radio" aria-checked={todo.priority === id} style={{ "--tone": tone }}
              onClick={() => onUpdate({ priority: id })}><Flag size={12} /> {label}</button>
          ))}
        </div>
      </div>
      <div className="te-field">
        <span>Due date</span>
        <div className="due-pick">
          <input className="input" type="date" value={todo.due_date || ""} onChange={(e) => onUpdate({ due_date: e.target.value || null })} aria-label="Due date" />
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => onUpdate({ due_date: todayIso() })}>Today</button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => onUpdate({ due_date: addDays(1) })}>Tomorrow</button>
          {todo.due_date && <button type="button" className="btn btn-ghost btn-sm" onClick={() => onUpdate({ due_date: null })}>Clear</button>}
        </div>
      </div>
      <label className="te-field">
        <span>Subject</span>
        <select className="select" value={todo.subject || ""} onChange={(e) => onUpdate({ subject: e.target.value || null })}>
          <option value="">No subject</option>
          {app.subjects.map((s) => <option key={s.slug} value={s.slug}>{s.title}</option>)}
        </select>
      </label>
      <div className="te-field">
        <span>Tags</span>
        <TagInput tags={todo.tags || []} onChange={(tags) => onUpdate({ tags })} />
      </div>
      <div className="te-field wide">
        <span>Steps {subtasks.length > 0 && `· ${subtasks.filter((s) => s.done).length}/${subtasks.length} done`}</span>
        <ul className="subtask-list">
          {subtasks.map((s, i) => (
            <li key={i} className={s.done ? "done" : ""}>
              <button type="button" className="check sm" role="checkbox" aria-checked={s.done} aria-label={s.text}
                onClick={() => setSubtasks(subtasks.map((x, j) => (j === i ? { ...x, done: !x.done } : x)))}>
                {s.done && <Check size={11} />}
              </button>
              <span>{s.text}</span>
              <button type="button" className="icon-btn" aria-label={`Remove step ${s.text}`}
                onClick={() => setSubtasks(subtasks.filter((_, j) => j !== i))}><X size={13} /></button>
            </li>
          ))}
        </ul>
        <div className="subtask-add">
          <input className="input" value={subtask} maxLength={200} placeholder="Add a step" aria-label="Add a step"
            onChange={(e) => setSubtask(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addSubtask(); } }} />
          <button type="button" className="btn btn-secondary btn-sm" onClick={addSubtask} disabled={!subtask.trim()}><Plus size={14} /> Add</button>
        </div>
      </div>
    </div>
  );
}

function TodoItem({ todo, open, selecting, selected, draggable, onToggleOpen, onSelect, onUpdate, onDuplicate, onDelete, dragProps }) {
  const { app } = useApp();
  const subject = app.subjects.find((s) => s.slug === todo.subject);
  const due = !todo.done && dueLabel(todo.due_date);
  const steps = todo.subtasks || [];
  const prio = PRIORITY[todo.priority] || PRIORITY.medium;
  return (
    <li className={`todo-item${todo.done ? " done" : ""}${open ? " open" : ""}${selected ? " selected" : ""}`}
      style={{ "--tone": prio.tone }} {...(open ? {} : dragProps)}>
      <div className="todo-row">
        {draggable && <span className="drag-handle" aria-hidden="true" title="Drag to reorder"><GripVertical size={15} /></span>}
        {selecting ? (
          <input type="checkbox" className="select-box" checked={selected} onChange={() => onSelect(todo.id)} aria-label={`Select ${todo.title}`} />
        ) : (
          <button type="button" className="check" role="checkbox" aria-checked={todo.done} aria-label={`Mark ${todo.title} as ${todo.done ? "not done" : "done"}`}
            onClick={() => onUpdate({ done: !todo.done })}>{todo.done && <Check size={13} />}</button>
        )}
        <button type="button" className="todo-title" onClick={onToggleOpen} aria-expanded={open}>
          <span className="tt">{todo.title}</span>
          <span className="todo-meta">
            <span className="prio-pill"><Flag size={11} /> {prio.label}</span>
            {due && <span className={`due ${due.state}`}><CalendarDays size={11} /> {due.text}</span>}
            {todo.done && todo.completed_at && <span className="due">Done {new Date(todo.completed_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>}
            {steps.length > 0 && <span><ListChecks size={11} /> {steps.filter((s) => s.done).length}/{steps.length}</span>}
            {todo.notes && <span className="note-dot">Notes</span>}
            {(todo.tags || []).map((tag) => <span key={tag} className="todo-tag">#{tag}</span>)}
          </span>
        </button>
        {subject && <SubjectArt subject={subject} size={30} />}
        <div className="todo-actions">
          {todo.link && (
            <Link className="btn btn-secondary btn-sm todo-open" to={todo.link} title="Open the page this task is about"><ExternalLink size={13} /> Open</Link>
          )}
          <button type="button" className="icon-btn" title="Duplicate" aria-label={`Duplicate ${todo.title}`} onClick={onDuplicate}><Copy size={14} /></button>
          <button type="button" className="icon-btn" title="Delete" aria-label={`Delete ${todo.title}`} onClick={onDelete}><Trash2 size={14} /></button>
          <button type="button" className="icon-btn" aria-label={open ? "Close details" : "Edit details"} onClick={onToggleOpen}>
            <ChevronDown size={15} style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
          </button>
        </div>
      </div>
      {open && <TodoEditor todo={todo} onUpdate={onUpdate} />}
    </li>
  );
}

export default function Todos() {
  const { app, user, notify, t, lang } = useApp();
  const [todos, setTodos] = useState(null);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("medium");
  const [due, setDue] = useState("");
  const [subject, setSubject] = useState("");
  const [view, setView] = useState("active");
  const [sort, setSort] = useState("manual");
  const [subjectFilter, setSubjectFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [openId, setOpenId] = useState(null);
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState(() => new Set());
  const [confirm, setConfirm] = useState(null); // { title, body, run }
  const dragId = useRef(null);
  const [dragOver, setDragOver] = useState(null);
  const inputRef = useRef(null);
  useCrumbs([{ label: t("nav_todos") }]);

  const load = useCallback(() => api("/api/todos").then((res) => setTodos(res.todos)).catch(() => setTodos([])), []);
  useEffect(() => { load(); }, [load, user?.id]);

  const today = todayIso();
  const counts = useMemo(() => {
    const list = todos || [];
    return {
      all: list.length,
      active: list.filter((t) => !t.done).length,
      today: list.filter((t) => !t.done && t.due_date === today).length,
      upcoming: list.filter((t) => !t.done && t.due_date && t.due_date > today).length,
      overdue: list.filter((t) => !t.done && t.due_date && t.due_date < today).length,
      done: list.filter((t) => t.done).length,
    };
  }, [todos, today]);

  const shown = useMemo(() => {
    let list = (todos || []).filter((t) => {
      if (view === "active" && t.done) return false;
      if (view === "done" && !t.done) return false;
      if (view === "today" && (t.done || t.due_date !== today)) return false;
      if (view === "upcoming" && (t.done || !t.due_date || t.due_date <= today)) return false;
      if (view === "overdue" && (t.done || !t.due_date || t.due_date >= today)) return false;
      if (subjectFilter !== "all" && (t.subject || "none") !== subjectFilter) return false;
      const q = query.trim().toLowerCase();
      return !q || `${t.title} ${t.notes || ""} ${(t.tags || []).join(" ")}`.toLowerCase().includes(q);
    });
    if (sort === "due") list = [...list].sort((a, b) => (a.due_date || "9999").localeCompare(b.due_date || "9999"));
    if (sort === "priority") list = [...list].sort((a, b) => PRIORITY[a.priority].rank - PRIORITY[b.priority].rank);
    if (sort === "newest") list = [...list].sort((a, b) => b.id - a.id);
    return list;
  }, [todos, view, today, subjectFilter, query, sort]);

  const add = async (event) => {
    event.preventDefault();
    if (!title.trim()) return;
    try {
      const { todo } = await api("/api/todos", {
        method: "POST", body: { title: title.trim(), priority, due_date: due || null, subject: subject || null },
      });
      setTodos((list) => [todo, ...(list || [])]);
      setTitle("");
      setDue("");
      if (view === "done") setView("active");
      inputRef.current?.focus();
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };

  const update = async (id, patch) => {
    setTodos((list) => list.map((t) => (t.id === id ? { ...t, ...patch } : t)));
    try {
      const { todo } = await api(`/api/todos/${id}`, { method: "PATCH", body: patch });
      setTodos((list) => list.map((t) => (t.id === id ? todo : t)));
      if (patch.done) notify(`Done: ${todo.title}`);
    } catch (err) {
      notify(err.message, { kind: "error" });
      load();
    }
  };

  const duplicate = async (id) => {
    try {
      const { todo } = await api(`/api/todos/${id}/duplicate`, { method: "POST", body: {} });
      setTodos((list) => {
        const i = list.findIndex((t) => t.id === id);
        const next = [...list];
        next.splice(i + 1, 0, todo);
        return next;
      });
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };

  // Deleted tasks can be brought back from the toast for a few seconds.
  const positions = useRef(new Map());
  const hideTodo = useCallback((todo) => setTodos((list) => {
    positions.current.set(todo.id, list.findIndex((t) => t.id === todo.id));
    return list.filter((t) => t.id !== todo.id);
  }), []);
  const restoreTodo = useCallback((todo) => setTodos((list) => {
    if (list.some((t) => t.id === todo.id)) return list;
    const next = [...list];
    next.splice(Math.min(positions.current.get(todo.id) ?? 0, next.length), 0, todo);
    return next;
  }), []);
  const removeTodo = useUndoableDelete({ hide: hideTodo, restore: restoreTodo, path: todoPath });

  const bulk = async (action, ids) => {
    try {
      const { changed } = await api("/api/todos/bulk", { method: "POST", body: { action, ids } });
      notify(`${changed} task${changed === 1 ? "" : "s"} updated`);
      setSelected(new Set());
      setSelecting(false);
      load();
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };

  const toggleSelect = (id) => setSelected((set) => {
    const next = new Set(set);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });

  // Drag and drop reordering (in "My order").
  const reorder = async (fromId, toId) => {
    if (fromId === toId) return;
    const list = [...todos];
    const from = list.findIndex((t) => t.id === fromId);
    const [moved] = list.splice(from, 1);
    list.splice(list.findIndex((t) => t.id === toId), 0, moved);
    setTodos(list);
    try {
      await api("/api/todos/reorder", { method: "POST", body: { ids: list.filter((t) => !t.done).map((t) => t.id) } });
    } catch (err) {
      notify(err.message, { kind: "error" });
      load();
    }
  };
  const canDrag = sort === "manual" && !selecting && view !== "done";
  const dragProps = (todo) => (canDrag && !todo.done ? {
    draggable: true,
    onDragStart: (e) => { dragId.current = todo.id; e.dataTransfer.effectAllowed = "move"; },
    onDragOver: (e) => { e.preventDefault(); setDragOver(todo.id); },
    onDragLeave: () => setDragOver((id) => (id === todo.id ? null : id)),
    onDrop: (e) => { e.preventDefault(); setDragOver(null); reorder(dragId.current, todo.id); },
    onDragEnd: () => { dragId.current = null; setDragOver(null); },
    "data-drag-over": dragOver === todo.id || undefined,
  } : {});

  const percent = counts.all ? Math.round((counts.done / counts.all) * 100) : 0;

  return (
    <>
      <section className="todo-hero">
        <div>
          <span className="eyebrow">Plan your studies</span>
          <h1>{t("nav_todos")}</h1>
          <p className="lede">{t("todo_sub")} {lang === "en" ? "Add steps, due dates and subjects, then tick them off." : ""}</p>
        </div>
        <div className="todo-progress" aria-label="Completion">
          <svg viewBox="0 0 80 80" width="92" height="92" aria-hidden="true">
            <circle cx="40" cy="40" r="33" fill="none" stroke="var(--rule)" strokeWidth="8" />
            <circle cx="40" cy="40" r="33" fill="none" stroke="var(--c-leaf)" strokeWidth="8" strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 33} strokeDashoffset={2 * Math.PI * 33 * (1 - percent / 100)}
              transform="rotate(-90 40 40)" style={{ transition: "stroke-dashoffset 0.8s" }} />
          </svg>
          <div>
            <b><CountUp value={percent} />%</b>
            <span>{counts.done} of {counts.all} done</span>
            {counts.overdue > 0 && <span className="overdue-note">{counts.overdue} overdue</span>}
          </div>
        </div>
      </section>

      <form className="todo-add" onSubmit={add}>
        <Plus size={18} className="muted" aria-hidden="true" />
        <label className="sr-only" htmlFor="todo-title">New task</label>
        <input id="todo-title" ref={inputRef} value={title} maxLength={200} autoComplete="off"
          placeholder="Add a task, e.g. Revise chapter 3 of Science" onChange={(e) => setTitle(e.target.value)} />
        <select className="select" aria-label="Priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
          {PRIORITIES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
        <input className="input" type="date" aria-label="Due date" value={due} onChange={(e) => setDue(e.target.value)} />
        <select className="select" aria-label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)}>
          <option value="">No subject</option>
          {app.subjects.map((s) => <option key={s.slug} value={s.slug}>{s.title}</option>)}
        </select>
        <button className="btn" type="submit" disabled={!title.trim()}>{t("add_task")}</button>
      </form>

      <div className="todo-views" role="tablist" aria-label="Show">
        {VIEWS.map((id) => (
          <button key={id} type="button" role="tab" aria-selected={view === id} onClick={() => setView(id)}
            className={id === "overdue" && counts.overdue ? "has-overdue" : ""}>
            {t(`view_${id}`)} <span className="count">{counts[id]}</span>
          </button>
        ))}
      </div>

      <div className="history-toolbar">
        <label className="history-search">
          <Search size={15} aria-hidden="true" />
          <span className="sr-only">Search tasks</span>
          <input type="search" placeholder="Search tasks, notes and tags" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <select className="select" aria-label="Subject" value={subjectFilter} onChange={(e) => setSubjectFilter(e.target.value)} style={{ width: "auto" }}>
          <option value="all">All subjects</option>
          <option value="none">No subject</option>
          {app.subjects.map((s) => <option key={s.slug} value={s.slug}>{s.title}</option>)}
        </select>
        <label className="sort-pick">
          <ArrowDownUp size={14} aria-hidden="true" />
          <span className="sr-only">Sort</span>
          <select className="select" value={sort} onChange={(e) => setSort(e.target.value)} style={{ width: "auto" }}>
            {SORTS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
        </label>
        <button type="button" className={`btn btn-sm ${selecting ? "" : "btn-secondary"}`} aria-pressed={selecting}
          onClick={() => { setSelecting((v) => !v); setSelected(new Set()); }}><SquareCheck size={14} /> {selecting ? "Done selecting" : "Select"}</button>
        {counts.done > 0 && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setConfirm({
            title: "Clear completed tasks", body: `Delete all ${counts.done} completed task${counts.done === 1 ? "" : "s"}?`,
            run: () => bulk("clear_completed", []),
          })}><Trash2 size={14} /> Clear completed</button>
        )}
      </div>

      {selecting && (
        <div className="bulk-bar" role="toolbar" aria-label="Selected tasks">
          <label><input type="checkbox" checked={shown.length > 0 && shown.every((t) => selected.has(t.id))}
            onChange={(e) => setSelected(e.target.checked ? new Set(shown.map((t) => t.id)) : new Set())} /> Select all shown</label>
          <span className="muted small">{selected.size} selected</span>
          <span className="spacer" />
          <button type="button" className="btn btn-sm" disabled={!selected.size} onClick={() => bulk("complete", [...selected])}><CheckCheck size={14} /> Complete</button>
          <button type="button" className="btn btn-sm btn-secondary" disabled={!selected.size} onClick={() => bulk("reopen", [...selected])}><RotateCcw size={14} /> Reopen</button>
          <button type="button" className="btn btn-sm btn-danger" disabled={!selected.size} onClick={() => setConfirm({
            title: "Delete tasks", body: `Delete ${selected.size} selected task${selected.size === 1 ? "" : "s"}?`, run: () => bulk("delete", [...selected]),
          })}><Trash2 size={14} /> Delete</button>
        </div>
      )}

      {!todos ? <Loading /> : shown.length === 0 ? (
        <EmptyState icon={ListChecks} title={todos.length ? "Nothing here" : "Your list is empty"}>
          {todos.length ? "No tasks match this view." : "Add your first task above. Try “Finish maths worksheet” with a due date."}
        </EmptyState>
      ) : (
        <ul className="todo-list">
          {shown.map((todo) => (
            <TodoItem key={todo.id} todo={todo} open={openId === todo.id} selecting={selecting} selected={selected.has(todo.id)}
              draggable={canDrag && !todo.done} dragProps={dragProps(todo)}
              onToggleOpen={() => setOpenId((id) => (id === todo.id ? null : todo.id))}
              onSelect={toggleSelect} onUpdate={(patch) => update(todo.id, patch)}
              onDuplicate={() => duplicate(todo.id)}
              onDelete={() => removeTodo(todo, `Deleted “${todo.title}”`)} />
          ))}
        </ul>
      )}
      {todos && todos.length > 0 && (
        <p className="small muted" style={{ marginTop: 14 }}><Tag size={12} /> Tip: click a task to add notes, steps and tags. Drag tasks to reorder them in “My order”.</p>
      )}

      <Dialog open={Boolean(confirm)} onClose={() => setConfirm(null)} title={confirm?.title || ""}>
        <p>{confirm?.body} This can't be undone.</p>
        <div className="dialog-footer">
          <button className="btn btn-secondary" type="button" onClick={() => setConfirm(null)}>Cancel</button>
          <button className="btn btn-danger" type="button" onClick={() => { const run = confirm.run; setConfirm(null); run(); }}><Trash2 size={15} /> Delete</button>
        </div>
      </Dialog>
    </>
  );
}
