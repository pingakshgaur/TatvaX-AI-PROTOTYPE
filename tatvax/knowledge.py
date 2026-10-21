"""The content library: documents stored in the database, seeded from Markdown files,
plus a BM25 search index over their sections."""

import json
import math
import re
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .db import get_setting, now_iso, set_setting

KINDS = {"subjects": "subject", "helpdesk": "helpdesk"}

_FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_STOPWORDS = set(
    """a an the is are was were be been being am of to in on at for from by with and or not no
    what which who whom whose why how when where do does did can could should would will shall may
    might must i me my we our you your he she it its they them their this that these those there
    here about into over under than then so if as tell explain please give show define meaning mean
    describe know want need some any all more most also just very""".split()
    # Common Hindi function words, so they don't drown out the topic words of a question.
    + "है हैं था थे की के का को में से पर और या भी यह वह क्या कैसे क्यों कौन मुझे हम आप तुम एक इस उस".split()
)


def words(text: str) -> list[str]:
    """Split text into words in any script. A word is a run of letters, combining marks (the vowel
    signs and viramas of Indic scripts) and digits, so "प्रकाश" stays one word."""
    out, current = [], []
    for ch in text.lower():
        if unicodedata.category(ch)[0] in "LMN":
            current.append(ch)
        elif current:
            out.append("".join(current))
            current = []
    if current:
        out.append("".join(current))
    return out


def slugify(text: str) -> str:
    """URL name for a document: Latin titles become "social-studies", other scripts keep their own
    letters ("विज्ञान"), so a Hindi or Tamil subject still gets a readable, distinct address."""
    slug = "-".join(words(unicodedata.normalize("NFC", text)))[:60].strip("-")
    return slug or "untitled"


def parse_markdown_file(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    meta: dict[str, str] = {}
    match = _FRONT_MATTER.match(raw)
    if match:
        for line in match.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip().strip('"').strip("'")
        raw = raw[match.end():]
    return {
        "slug": path.stem,
        "title": meta.get("title", path.stem.replace("-", " ").title()),
        "description": meta.get("description", ""),
        "icon": meta.get("icon", "book"),
        "color": meta.get("color", "#2563eb"),
        "position": int(meta.get("order", 100)),
        "body": raw.strip() + "\n",
    }


def seed_documents(conn, content_dir: Path) -> int:
    """Import the bundled Markdown notes. Each bundled document is imported once: a new install gets
    them all, an upgraded install gets the ones added in the new version, and a document a teacher
    deleted or edited is left as the teacher left it. Returns the number imported."""
    bundled = [(path, kind) for folder, kind in KINDS.items() for path in sorted((content_dir / folder).glob("*.md"))]
    seeded_raw = get_setting(conn, "content_seeded")
    if seeded_raw is None:
        # First run of 2.6.1 or later. An install that already has documents imported the bundled
        # notes back then (seeding only ever filled an empty library), so count those as done.
        has_documents = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        seeded = {path.stem for path, _ in bundled} if has_documents else set()
    else:
        seeded = set(json.loads(seeded_raw))
    imported = 0
    for path, kind in bundled:
        if path.stem in seeded:
            continue
        seeded.add(path.stem)
        if conn.execute("SELECT 1 FROM documents WHERE slug = ?", (path.stem,)).fetchone():
            continue
        conn.execute(
            """INSERT INTO documents (slug, kind, title, description, icon, color, position, body, updated_at)
               VALUES (:slug, :kind, :title, :description, :icon, :color, :position, :body, :updated_at)""",
            {**parse_markdown_file(path), "kind": kind, "updated_at": now_iso()},
        )
        imported += 1
    set_setting(conn, "content_seeded", json.dumps(sorted(seeded)))
    conn.commit()
    return imported


def list_documents(conn, kind: str | None = None) -> list[dict]:
    query = "SELECT slug, kind, title, description, icon, color, position, updated_at FROM documents"
    params: tuple = ()
    if kind:
        query += " WHERE kind = ?"
        params = (kind,)
    rows = conn.execute(query + " ORDER BY kind, position, title", params).fetchall()
    return [dict(row) for row in rows]


def get_document(conn, slug: str) -> dict | None:
    row = conn.execute("SELECT * FROM documents WHERE slug = ?", (slug,)).fetchone()
    return dict(row) if row else None


def helpdesk_slug(conn) -> str | None:
    row = conn.execute("SELECT slug FROM documents WHERE kind = 'helpdesk' ORDER BY position LIMIT 1").fetchone()
    return row["slug"] if row else None


# --------------------------------------------------------------------------- search

@dataclass
class Section:
    slug: str
    doc_title: str
    heading: str       # "Chapter 2: Basic Operations › Addition"
    text: str          # Markdown body of the section, heading included


def split_sections(slug: str, title: str, body: str) -> list[Section]:
    """Split a document at '##'/'###' headings and at bold-only topic lines like '**Addition**'."""
    sections: list[Section] = []
    chapter = ""
    topic = ""
    buffer: list[str] = []

    def flush():
        text = "\n".join(buffer).strip()
        if len(text) > 30:
            heading = " › ".join(part for part in (chapter, topic) if part) or title
            sections.append(Section(slug, title, heading, text))
        buffer.clear()

    for line in body.splitlines():
        stripped = line.strip()
        heading_match = re.match(r"^(#{1,3})\s+(.*)", stripped)
        topic_match = re.match(r"^\*\*([^*]{2,80})\*\*:?$", stripped)
        if heading_match:
            flush()
            if len(heading_match.group(1)) <= 2:
                chapter, topic = heading_match.group(2).strip(), ""
            else:
                topic = heading_match.group(2).strip()
            continue
        if topic_match:
            flush()
            topic = topic_match.group(1).strip()
            buffer.append(f"**{topic}**")
            continue
        buffer.append(line)
    flush()
    return sections


def _singular(token: str) -> str:
    """Light plural stemming: properties -> property, classes -> class, fees -> fee, rights -> right."""
    if len(token) <= 3:
        return token
    if token.endswith("ies"):
        return token[:-3] + "y"
    if token.endswith(("sses", "ches", "shes", "xes")):
        return token[:-2]
    if token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    tokens = []
    for token in words(unicodedata.normalize("NFC", text)):
        if token in _STOPWORDS or len(token) < 2:
            continue
        tokens.append(_singular(token) if token.isascii() else token)
    return tokens


class LibraryIndex:
    """BM25 over document sections. Rebuilt lazily whenever a document changes."""

    def __init__(self, k1: float = 1.4, b: float = 0.75):
        self.k1, self.b = k1, b
        self._lock = threading.Lock()
        self._signature: tuple = ()
        self._sections: list[Section] = []
        self._tokens: list[list[str]] = []
        self._idf: dict[str, float] = {}
        self._avg_len = 1.0

    def _ensure_current(self, conn) -> None:
        signature = tuple(conn.execute("SELECT slug, updated_at FROM documents ORDER BY slug").fetchall())
        signature = tuple(tuple(row) for row in signature)
        if signature == self._signature:
            return
        with self._lock:
            if signature == self._signature:
                return
            sections: list[Section] = []
            for row in conn.execute("SELECT slug, title, body FROM documents"):
                sections.extend(split_sections(row["slug"], row["title"], row["body"]))
            tokens = [tokenize(f"{s.heading} {s.heading} {s.text}") for s in sections]
            doc_freq: dict[str, int] = {}
            for toks in tokens:
                for tok in set(toks):
                    doc_freq[tok] = doc_freq.get(tok, 0) + 1
            n = max(len(tokens), 1)
            self._idf = {tok: math.log(1 + (n - df + 0.5) / (df + 0.5)) for tok, df in doc_freq.items()}
            self._sections, self._tokens = sections, tokens
            self._avg_len = sum(len(t) for t in tokens) / n if tokens else 1.0
            self._signature = signature

    def sections_in(self, conn, slug: str) -> list[Section]:
        self._ensure_current(conn)
        return [s for s in self._sections if s.slug == slug]

    def search(self, conn, query: str, slugs: list[str] | None = None, limit: int = 3) -> list[tuple[Section, float]]:
        self._ensure_current(conn)
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        results = []
        for section, toks in zip(self._sections, self._tokens):
            if slugs and section.slug not in slugs:
                continue
            if not toks:
                continue
            score = 0.0
            for q in set(query_tokens):
                tf = toks.count(q)
                if not tf:
                    continue
                norm = tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * len(toks) / self._avg_len))
                score += self._idf.get(q, 0.0) * norm
            if score > 0:
                results.append((section, score))
        results.sort(key=lambda item: item[1], reverse=True)
        return results[:limit]


library_index = LibraryIndex()
