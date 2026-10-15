import { ChevronRight, ClipboardCheck, MessageSquareText, Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import { EmptyState, Loading, Markdown, PageHeader, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { subjectCode } from "../lib/format.js";

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
              <span className="subject-code" style={{ "--subject-color": d.color }}>{d.kind === "helpdesk" ? "HLP" : subjectCode(d.title)}</span>
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

const slugify = (text) => text.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "");

export function LibraryDocument() {
  const { t } = useApp();
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState("");
  const [toc, setToc] = useState([]);
  const [active, setActive] = useState("");
  const readerRef = useRef(null);

  useCrumbs([{ label: t("nav_library"), to: "/notes" }, { label: doc?.title || "…" }]);

  useEffect(() => {
    setDoc(null);
    setError("");
    api(`/api/library/${encodeURIComponent(slug)}`).then((res) => setDoc(res.document)).catch((err) => setError(err.message));
  }, [slug]);

  // Build the table of contents from the rendered chapter headings.
  useEffect(() => {
    const reader = readerRef.current;
    if (!doc || !reader) return undefined;
    const headings = [...reader.querySelectorAll("h2")];
    headings.forEach((h) => { h.id = `sec-${slugify(h.textContent)}`; });
    setToc(headings.map((h) => ({ id: h.id, label: h.textContent })));

    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (visible[0]) setActive(visible[0].target.id);
    }, { rootMargin: "-80px 0px -70% 0px" });
    headings.forEach((h) => observer.observe(h));

    const highlight = searchParams.get("h")?.toLowerCase();
    if (highlight) {
      const target = [...reader.querySelectorAll("h2, h3, h4, strong, p")].find((el) => el.textContent.toLowerCase().includes(highlight));
      if (target) {
        requestAnimationFrame(() => {
          target.scrollIntoView({ behavior: "smooth", block: "center" });
          target.classList.add("flash");
        });
      }
    }
    return () => observer.disconnect();
  }, [doc, searchParams]);

  if (error) return <EmptyState title="Notes not found" action={<Link className="btn" to="/notes">{t("library_title")}</Link>}>{error}</EmptyState>;
  if (!doc) return <Loading />;

  const tutorLink = doc.kind === "helpdesk" ? "/helpdesk" : `/learn/${doc.slug}`;
  return (
    <>
      <PageHeader eyebrow={doc.kind === "helpdesk" ? "School information" : "Subject notes"} title={doc.title} lede={doc.description}
        actions={<>
          <Link className="btn" to={tutorLink}><MessageSquareText size={15} /> {t("ask_about")}</Link>
          {doc.kind === "subject" && <Link className="btn btn-secondary" to={`/assessments/${doc.slug}`}><ClipboardCheck size={15} /> {t("nav_quiz")}</Link>}
        </>} />
      <div className="reader-layout">
        <nav className="toc" aria-label={t("contents")}>
          <span className="eyebrow" style={{ display: "block", padding: "0 10px 8px" }}>{t("contents")}</span>
          {toc.map((item) => (
            <a key={item.id} href={`#${item.id}`} className={active === item.id ? "active" : ""}
              onClick={(e) => { e.preventDefault(); document.getElementById(item.id)?.scrollIntoView({ behavior: "smooth" }); }}>
              {item.label}
            </a>
          ))}
        </nav>
        <div>
          <NotesSearch subject={doc.slug} />
          <Panel><div ref={readerRef}><Markdown className="prose reader" source={doc.body} /></div></Panel>
        </div>
      </div>
    </>
  );
}
