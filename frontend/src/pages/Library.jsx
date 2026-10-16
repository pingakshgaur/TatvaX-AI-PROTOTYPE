import { CheckCircle2, ChevronRight, ClipboardCheck, FileDown, Lightbulb, MessageSquareText, Search, Sigma, Star } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import SubjectArt from "../components/SubjectArt.jsx";
import { EmptyState, Loading, Markdown, Meter, PageHeader, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";

function NotesSearch({ subject }) {
  const { t } = useApp();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");

  const run = async (event) => {
    event.preventDefault();
    if (!query.trim()) { setResults(null); return; }
    const params = new URLSearchParams({ q: query.trim() });
    if (subject) params.set("subject", subject);
    try {
      setError("");
      setResults((await api(`/api/search?${params}`)).results);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={{ marginBottom: 20 }}>
      <form className="command-bar" role="search" onSubmit={run}>
        <Search size={17} className="muted" aria-hidden="true" />
        <label className="sr-only" htmlFor="notes-search">{t("search_notes")}</label>
        <input id="notes-search" type="search" dir="auto" placeholder={t("search_notes")} value={query} onChange={(e) => setQuery(e.target.value)} />
        <button className="btn btn-secondary" type="submit">Search</button>
      </form>
      {error && <p className="form-error">{error}</p>}
      {results && (
        <Panel tight className="section" title={`${results.length} result${results.length === 1 ? "" : "s"}`}>
          {results.length === 0 && <div className="panel-body muted">{t("no_results")}</div>}
          {results.map((r) => (
            <Link key={`${r.slug}-${r.heading}`} className="search-result"
              to={`/notes/${r.slug}?h=${encodeURIComponent(r.heading.split(" › ").pop())}`}>
              <span className="eyebrow">{r.title} / {r.heading}</span>
              <p>{r.excerpt.replace(/[*#]/g, "").slice(0, 220)}…</p>
            </Link>
          ))}
        </Panel>
      )}
    </div>
  );
}

export function LibraryIndex() {
  const { t } = useApp();
  const [documents, setDocuments] = useState(null);
  useCrumbs([{ label: t("nav_library") }]);

  useEffect(() => {
    api("/api/library").then((res) => setDocuments(res.documents)).catch(() => setDocuments([]));
  }, []);

  return (
    <>
      <PageHeader eyebrow={t("group_practice")} title={t("library_title")} lede={t("library_sub")} />
      <NotesSearch />
      {!documents ? <Loading /> : (
        <Panel tight title="Collections">
          {documents.map((d) => (
            <Link key={d.slug} className="list-row" to={`/notes/${d.slug}`}>
              <SubjectArt subject={d} size={42} />
              <span className="grow">
                <span className="title">{d.title}</span>
                <span className="desc" style={{ display: "block" }}>{d.description}</span>
              </span>
              <span className="tag">{d.kind === "helpdesk" ? "School information" : "Subject notes"}</span>
              <ChevronRight className="chev" size={18} aria-hidden="true" />
            </Link>
          ))}
        </Panel>
      )}
    </>
  );
}

const CHAPTER_TONES = ["var(--c-teal)", "var(--c-indigo)", "var(--c-coral)", "var(--c-leaf)", "var(--c-plum)", "var(--c-saffron)"];
export const CALLOUTS = [
  [/^(Examples?|Solve|Answer|To solve)\s*:/i, "example", Lightbulb],
  [/^(Remember|Note|Important|Tip)\s*:/i, "note", Star],
  [/^(Symbol|Formula|Formulas)\s*:/i, "formula", Sigma],
];

// Split a document into chapters ("## ...") and topics ("### ..." or a "**Topic**" line).
export function parseNotes(body) {
  const chapters = [];
  let chapter = null;
  let topic = null;
  const startChapter = (title) => {
    const match = title.match(/^Chapter\s+(\d+)\s*[:.-]\s*(.*)$/i);
    chapter = { number: match ? match[1] : String(chapters.length + 1), title: match ? match[2] : title, intro: [], topics: [] };
    chapters.push(chapter);
    topic = null;
  };
  for (const line of body.replace(/\r\n/g, "\n").split("\n")) {
    const heading = line.match(/^#{1,2}\s+(.*)/);
    const sub = line.match(/^#{3,4}\s+(.*)/) || line.trim().match(/^\*\*([^*]{2,80})\*\*:?$/);
    if (heading) { startChapter(heading[1].trim()); continue; }
    if (!chapter) startChapter("Introduction");
    if (sub) {
      topic = { title: sub[1].trim().replace(/:$/, ""), lines: [] };
      chapter.topics.push(topic);
      continue;
    }
    (topic ? topic.lines : chapter.intro).push(line);
  }
  return chapters.filter((c) => c.topics.length || c.intro.join("").trim());
}

// Group a topic's lines into plain Markdown and coloured callouts.
export function segments(lines) {
  const out = [];
  let current = null;
  for (const line of lines) {
    const callout = CALLOUTS.find(([pattern]) => pattern.test(line.trim()));
    if (callout) {
      current = { kind: callout[1], icon: callout[2], lines: [line.trim()] };
      out.push(current);
    } else if (current && current.kind !== "md" && line.trim() && !/^\*\*/.test(line.trim())
      // A callout continues with list items and short labelled lines ("Positive integers: 1, 2, 3").
      && (/^\s*([-*•]|\d+[.)])\s/.test(line) || /^[^.:]{2,32}:/.test(line.trim()))) {
      current.lines.push(line);
    } else {
      if (!current || current.kind !== "md") {
        current = { kind: "md", lines: [] };
        out.push(current);
      }
      current.lines.push(line);
    }
    if (!line.trim() && current && current.kind !== "md") current = null;
  }
  return out.filter((s) => s.lines.join("").trim());
}

function readKey(slug) { return `tatvax.read.${slug}`; }

function loadRead(slug) {
  try { return new Set(JSON.parse(localStorage.getItem(readKey(slug)) || "[]")); } catch { return new Set(); }
}

function Topic({ topic, docSlug, kind }) {
  const { t } = useApp();
  const askHref = kind === "helpdesk"
    ? `/tatvai?q=${encodeURIComponent(`Tell me about ${topic.title}`)}`
    : `/learn/${docSlug}?q=${encodeURIComponent(`Explain ${topic.title} with an example`)}`;
  return (
    <div className="topic-card" data-topic={topic.title.toLowerCase()}>
      <h3>{topic.title}
        <Link className="btn btn-ghost btn-sm ask-topic" to={askHref}><MessageSquareText size={13} /> {t("ask_about")}</Link>
      </h3>
      {segments(topic.lines).map((seg, i) => {
        if (seg.kind === "md") return <Markdown key={i} source={seg.lines.join("\n")} />;
        const Icon = seg.icon;
        return (
          <div key={i} className={`callout ${seg.kind}`}>
            <Icon size={16} aria-hidden="true" />
            <Markdown source={seg.lines.join("\n")} />
          </div>
        );
      })}
    </div>
  );
}

export function LibraryDocument() {
  const { t } = useApp();
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState("");
  const [active, setActive] = useState("");
  const [read, setRead] = useState(() => loadRead(slug));
  const [scrolled, setScrolled] = useState(0);
  const notesRef = useRef(null);

  useCrumbs([{ label: t("nav_library"), to: "/notes" }, { label: doc?.title || "…" }]);

  useEffect(() => {
    setDoc(null);
    setError("");
    setRead(loadRead(slug));
    api(`/api/library/${encodeURIComponent(slug)}`).then((res) => setDoc(res.document)).catch((err) => setError(err.message));
  }, [slug]);

  const chapters = useMemo(() => (doc ? parseNotes(doc.body) : []), [doc]);

  // Reading progress bar.
  useEffect(() => {
    const onScroll = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setScrolled(max > 0 ? Math.min(1, window.scrollY / max) : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [chapters]);

  // Highlight the current chapter in the contents, and jump to a searched topic.
  useEffect(() => {
    const root = notesRef.current;
    if (!root || !chapters.length) return undefined;
    const sections = [...root.querySelectorAll(".chapter")];
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (visible[0]) setActive(visible[0].target.id);
    }, { rootMargin: "-80px 0px -65% 0px" });
    sections.forEach((s) => observer.observe(s));

    const wanted = searchParams.get("h")?.toLowerCase();
    if (wanted) {
      const target = root.querySelector(`[data-topic="${CSS.escape(wanted)}"]`)
        || [...root.querySelectorAll(".topic-card, .chapter-head")].find((el) => el.textContent.toLowerCase().includes(wanted));
      if (target) requestAnimationFrame(() => {
        target.scrollIntoView({ behavior: "smooth", block: "center" });
        target.classList.add("flash");
      });
    }
    return () => observer.disconnect();
  }, [chapters, searchParams]);

  const toggleRead = (id) => setRead((set) => {
    const next = new Set(set);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    try { localStorage.setItem(readKey(slug), JSON.stringify([...next])); } catch { /* storage unavailable */ }
    return next;
  });

  if (error) return <EmptyState title="Notes not found" action={<Link className="btn" to="/notes">{t("library_title")}</Link>}>{error}</EmptyState>;
  if (!doc) return <Loading />;

  const tutorLink = doc.kind === "helpdesk" ? "/tatvai" : `/learn/${doc.slug}`;
  const readCount = chapters.filter((c, i) => read.has(`ch-${i}`)).length;

  return (
    <>
      <div className="reading-progress" aria-hidden="true"><span style={{ width: `${scrolled * 100}%` }} /></div>
      <PageHeader eyebrow={doc.kind === "helpdesk" ? "School information" : "Subject notes"} title={doc.title} lede={doc.description}
        actions={<>
          <Link className="btn" to={tutorLink}><MessageSquareText size={15} /> {t("ask_about")}</Link>
          {doc.kind === "subject" && <Link className="btn btn-secondary" to={`/assessments/${doc.slug}`}><ClipboardCheck size={15} /> {t("nav_quiz")}</Link>}
          <a className="btn btn-ghost" href={`/print/notes/${doc.slug}`} target="_blank" rel="noopener"><FileDown size={15} /> {t("export_pdf")}</a>
        </>} />
      <div className="reader-layout">
        <nav className="toc" aria-label={t("contents")}>
          <span className="eyebrow" style={{ display: "block", padding: "0 10px 8px" }}>{t("contents")} · {readCount}/{chapters.length} read</span>
          <div className="read-meter"><Meter value={chapters.length ? readCount / chapters.length : 0} label="Chapters read" /></div>
          {chapters.map((c, i) => (
            <a key={i} href={`#ch-${i}`} className={`${active === `ch-${i}` ? "active" : ""}${read.has(`ch-${i}`) ? " read" : ""}`}
              style={{ "--tone": CHAPTER_TONES[i % CHAPTER_TONES.length] }}
              onClick={(e) => { e.preventDefault(); document.getElementById(`ch-${i}`)?.scrollIntoView({ behavior: "smooth" }); }}>
              <span className="toc-dot" aria-hidden="true" />{c.title}
              {read.has(`ch-${i}`) && <CheckCircle2 className="toc-check" size={14} aria-label="Read" />}
            </a>
          ))}
        </nav>
        <div>
          <NotesSearch subject={doc.slug} />
          <div className="notes stagger" ref={notesRef}>
            {chapters.map((chapter, i) => {
              const id = `ch-${i}`;
              const done = read.has(id);
              return (
                <section key={id} id={id} className="chapter" style={{ "--tone": CHAPTER_TONES[i % CHAPTER_TONES.length], "--i": Math.min(i, 6) }}>
                  <header className="chapter-head">
                    <span className="chapter-num" aria-hidden="true">{chapter.number}</span>
                    <div>
                      <span className="eyebrow">Chapter {chapter.number} · {chapter.topics.length} topics</span>
                      <h2>{chapter.title}</h2>
                    </div>
                    <div className="ch-actions">
                      {doc.kind === "subject" && (
                        <Link className="btn btn-sm" to={`/assessments/${doc.slug}?topic=${encodeURIComponent(chapter.title)}`}>
                          <ClipboardCheck size={14} /> <span>Quiz me</span>
                        </Link>
                      )}
                      <button className={`btn btn-sm${done ? " done" : ""}`} type="button" aria-pressed={done} onClick={() => toggleRead(id)}>
                        <CheckCircle2 size={14} /> <span>{done ? "Read" : "Mark as read"}</span>
                      </button>
                    </div>
                  </header>
                  <div className="chapter-body">
                    {chapter.intro.join("\n").trim() && <Markdown source={chapter.intro.join("\n")} />}
                    {chapter.topics.map((topic, j) => <Topic key={j} topic={topic} docSlug={doc.slug} kind={doc.kind} />)}
                  </div>
                </section>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
