"""Follow-up question suggestions shown after every answer.

With the AI tutor, the model writes them after a marker at the end of its answer, so no extra
request is needed; FollowupSplitter keeps them out of the streamed answer. Without the AI (or if
the model leaves them out), suggestions come from neighbouring topics in the study notes."""

import re

from .knowledge import library_index

MARKER = "@@FOLLOWUPS@@"
MAX_SUGGESTIONS = 3

INSTRUCTION = (
    f"\n\nAfter your answer, write a line containing only {MARKER} and then exactly three short follow-up "
    "questions the student could ask next, one per line, with no numbering. Each must build on this answer, "
    "be written in the reply language as the student would ask it, and be different from every question "
    "the student has already asked in this conversation."
)


class FollowupSplitter:
    """Passes answer text through and captures everything after the marker, even when the
    marker is split across streamed chunks."""

    def __init__(self):
        self.buffer = ""
        self.tail: str | None = None

    def feed(self, text: str) -> str:
        if self.tail is not None:
            self.tail += text
            return ""
        self.buffer += text
        index = self.buffer.find(MARKER)
        if index >= 0:
            visible, self.tail = self.buffer[:index], self.buffer[index + len(MARKER):]
            self.buffer = ""
            return visible
        # Hold back a trailing fragment that could be the start of the marker.
        keep = 0
        for size in range(min(len(MARKER) - 1, len(self.buffer)), 0, -1):
            if MARKER.startswith(self.buffer[-size:]):
                keep = size
                break
        visible = self.buffer[:len(self.buffer) - keep]
        self.buffer = self.buffer[len(self.buffer) - keep:]
        return visible

    def finish(self) -> tuple[str, str]:
        """Returns (remaining visible text, follow-up block)."""
        rest, self.buffer = self.buffer, ""
        return rest, self.tail or ""


def _normal(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def parse(block: str, asked: list[str]) -> list[str]:
    seen = {_normal(q) for q in asked}
    out = []
    for line in block.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip().strip('"“”').strip()
        line = line.replace("**", "")
        if not line or len(line) > 160 or _normal(line) in seen:
            continue
        seen.add(_normal(line))
        out.append(line)
        if len(out) == MAX_SUGGESTIONS:
            break
    return out


def _topic_name(heading: str) -> str:
    topic = heading.split(" › ")[-1]
    topic = re.sub(r"^\d+\.\s*", "", topic)                 # "1. Nouns" -> "Nouns"
    topic = re.sub(r"^Chapter \d+:\s*", "", topic)          # "Chapter 3: Force and Motion" -> "Force and Motion"
    topic = re.sub(r"\s*\([^)]*\)\s*$", "", topic)          # "Period (.)" -> "Period"
    return topic.rstrip(":").strip()


def from_notes(conn, query: str, slugs: list[str], mode: str, asked: list[str]) -> list[str]:
    """Suggest neighbouring topics from the same chapter of the notes that haven't come up yet."""
    hits = library_index.search(conn, query, slugs, limit=3)
    if not hits:
        return []
    asked_text = " ".join(asked).lower()
    top = hits[0][0]
    chapter = top.heading.split(" › ")[0]
    used = {_topic_name(s.heading).lower() for s, _ in hits}

    candidates: list[str] = []
    for section in library_index.sections_in(conn, top.slug):
        name = _topic_name(section.heading)
        if (section.heading.startswith(chapter) and name.lower() not in used and name.lower() not in asked_text
                and 2 < len(name) < 60 and name.lower() not in {"example", "examples", "key features", "applications"}):
            candidates.append(name)
            used.add(name.lower())
    current = _topic_name(top.heading)

    if mode == "helpdesk":
        templates = ["What should I know about {a}?", "Tell me about {a}.", "Can you explain {a}?"]
        suggestions = [templates[i % len(templates)].format(a=name) for i, name in enumerate(candidates[:MAX_SUGGESTIONS])]
    else:
        def ask_about(name: str, i: int) -> str:
            if name.endswith("?"):
                return name  # the notes already phrase this topic as a question
            return (f"Explain {name} step by step.", f"Tell me about {name}.")[i % 2]

        suggestions = []
        if current and not current.endswith("?") and current.lower() not in asked_text:
            suggestions.append(f"Can you give me an example of {current}?")
        for i, name in enumerate(candidates):
            if len(suggestions) >= MAX_SUGGESTIONS:
                break
            suggestions.append(ask_about(name, i))
        if len(suggestions) < MAX_SUGGESTIONS and current and not current.endswith("?"):
            suggestions.append(f"Why is {current} important?")
        if len(suggestions) < MAX_SUGGESTIONS and chapter:
            suggestions.append(f"Quiz me on {_topic_name(chapter)}.")
    return parse("\n".join(suggestions), asked)
