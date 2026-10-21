"""Answer a student's question: an NVIDIA-hosted model grounded in the content library when available,
otherwise the offline library search engine. Produces a stream of event dicts."""

import json
import logging
import re
from collections.abc import Iterator

from . import followups, gamification, knowledge, languages
from .ai import AIService, AIUnavailable, ImagesUnsupported
from .db import now_iso
from .knowledge import library_index
from .translation import TranslationError, Translator

log = logging.getLogger(__name__)

HISTORY_MESSAGES = 16
# Notes up to this size go into the prompt whole; anything larger sends only the best-matching
# sections. Short prompts are what keep the first words of an answer arriving quickly.
INLINE_LIBRARY_LIMIT = 4_000

TUTOR_PROMPT = """You are TatvaX, a warm and patient AI tutor for school students in India (classes 1-12). \
Students write in many Indian languages and often mix languages; always reply in the language named in the \
student context, using simple words for their class level. When a technical term has no common equivalent in \
that language, give the English term in brackets.

Teach rather than just tell: explain the idea step by step, use small examples from everyday Indian life \
(cricket scores, rupees, rotis, monsoon), and for a calculation show each step. Keep answers focused and \
readable on a phone: short paragraphs, Markdown headings or lists only when they help, and **bold** for key \
terms. Don't use emoji. Write maths with LaTeX between $...$ (inline) or $$...$$ (display). When it would help the student \
check their understanding, end with one short practice question.

The school's own study notes are provided below. Prefer them, and keep your explanation consistent with \
them. If a question goes beyond the notes, answer from your own knowledge at the right level for a school \
student. If a question is unrelated to studies, answer briefly and kindly steer back to learning.

Keep everything age-appropriate. If a student seems upset, unsafe or mentions self-harm, respond with care, \
encourage them to talk to a parent, teacher or another trusted adult, and mention that they can call the \
free Tele-MANAS helpline at 14416."""

HELPDESK_PROMPT = """You are TatvAI, the friendly AI companion of a school in India. Students and parents chat with you about anything school-related: admissions, fees, timings, exams, transport, facilities and rules, as well as study plans, exam preparation, motivation and everyday learning questions. Reply in the language named in the student context, in short clear sentences, without emoji.

For questions about this school, use only the school information provided below. Never guess or invent fees, dates, phone numbers, names or policies; if a school detail isn't in the information, say so plainly and suggest contacting the school office. For general study or wellbeing questions, help warmly and practically. Use short lists for steps or requirements. Keep everything respectful and age-appropriate. If a student seems upset, unsafe or mentions self-harm, respond with care, encourage them to talk to a trusted adult, and mention the free Tele-MANAS helpline at 14416."""

NOT_FOUND = {
    "subject": (
        "I couldn't find that topic in the study notes yet. Try asking with different words, "
        "pick a more specific subject, or ask your teacher."
    ),
    "helpdesk": (
        "I couldn't find that in the school's information. "
        "Please contact the school office for the exact details."
    ),
}


PHOTO_MARK = "[Photo] "  # prefix of a saved question that came with a picture


class Tutor:
    def __init__(self, ai: AIService, translator: Translator):
        self.ai = ai
        self.translator = translator

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def resolve_scope(conn, mode: str, subject: str | None) -> tuple[list[dict], str | None]:
        """Return (documents in scope, stored subject slug) or raise ValueError."""
        if mode == "helpdesk":
            docs = [d for d in knowledge.list_documents(conn, "helpdesk")]
            if not docs:
                raise ValueError("TatvAI has no school information yet")
            return [knowledge.get_document(conn, d["slug"]) for d in docs], docs[0]["slug"]
        if mode != "subject":
            raise ValueError("Unknown mode")
        if not subject or subject == "all":
            docs = knowledge.list_documents(conn, "subject")
            return [knowledge.get_document(conn, d["slug"]) for d in docs], "all"
        doc = knowledge.get_document(conn, subject)
        if doc is None or doc["kind"] != "subject":
            raise ValueError("Unknown subject")
        return [doc], subject

    @staticmethod
    def student_context(user, language: str) -> str:
        name, native = languages.english_name(language), languages.LANGUAGES[language][1]
        grade = f"Class {user['grade']}" if user["grade"] else "not specified"
        display_name = user["name"] if user["name"] and user["name"] != "Learner" else "not given"
        return (
            "<student_context>\n"
            f"Student name: {display_name}\nClass: {grade}\nReply language: {name} ({native})\n"
            "</student_context>"
        )

    def build_system(self, mode: str, docs: list[dict]) -> tuple[str, bool]:
        """The system prompt, with the notes inlined when they're small enough. Returns (prompt, notes_inlined)."""
        prompt = (HELPDESK_PROMPT if mode == "helpdesk" else TUTOR_PROMPT) + followups.INSTRUCTION
        notes = "\n\n".join(
            f'<notes title="{d["title"]}">\n{d["body"].strip()}\n</notes>' for d in docs
        )
        if len(notes) > INLINE_LIBRARY_LIMIT:
            return prompt, False
        return f"{prompt}\n\n<library>\n{notes}\n</library>", True

    def retrieved_notes(self, conn, question: str, docs: list[dict]) -> str:
        hits = library_index.search(conn, question, [d["slug"] for d in docs], limit=6)
        if not hits:
            return ""
        joined = "\n\n".join(f"### {s.doc_title} › {s.heading}\n{s.text}" for s, _ in hits)
        return f"<relevant_notes>\n{joined}\n</relevant_notes>\n\n"

    def library_answer(self, conn, question: str, mode: str, docs: list[dict], language: str) -> tuple[str, list[str]]:
        """Offline answer assembled from the best-matching sections of the notes."""
        query = question
        if languages.detect_language(question) != "en":
            try:
                query, _ = self.translator.translate(question, "en")
            except TranslationError:
                pass  # search with the original text; numbers and English terms may still match

        hits = library_index.search(conn, query, [d["slug"] for d in docs], limit=3)
        if hits:
            best = hits[0][1]
            hits = [(s, score) for s, score in hits if score >= best * 0.6]
        if not hits:
            answer, sources = NOT_FOUND[mode], []
        else:
            parts = [f"Here's what the **{hits[0][0].doc_title}** notes say:"]
            for section, _ in hits:
                text = section.text
                topic_line = text.split("\n", 1)
                if topic_line[0].startswith("**") and len(topic_line) > 1:
                    text = topic_line[1].strip()  # the heading below already names the topic
                parts.append(f"#### {section.heading}\n{text}")
            answer = "\n\n".join(parts)
            sources = [f"{s.doc_title} › {s.heading}" for s, _ in hits]

        if language != "en":
            try:
                answer, _ = self.translator.translate(answer.replace("**", ""), language, "en")
            except TranslationError:
                answer += "\n\n_(Translation is unavailable right now, so this answer is in English.)_"
        return answer, sources

    @staticmethod
    def _asked(conn, conversation_id: int):
        return conn.execute(
            "SELECT content FROM messages WHERE conversation_id = ? AND role = 'user' ORDER BY id", (conversation_id,)
        ).fetchall()

    def note_suggestions(self, conn, question: str, mode: str, docs: list[dict], language: str, asked: list[str]) -> list[str]:
        """Follow-up ideas from neighbouring topics in the notes, translated for the student."""
        query = question
        if languages.detect_language(question) != "en":
            try:
                query, _ = self.translator.translate(question, "en")
            except TranslationError:
                pass
        suggestions = followups.from_notes(conn, query, [d["slug"] for d in docs], mode, asked)
        if suggestions and language != "en":
            try:
                translated, _ = self.translator.translate("\n".join(suggestions), language, "en")
                lines = [line.strip() for line in translated.split("\n") if line.strip()]
                if len(lines) == len(suggestions):
                    suggestions = lines
            except TranslationError:
                pass
        return suggestions

    @staticmethod
    def load_history(conn, conversation_id: int) -> list[dict]:
        rows = conn.execute(
            "SELECT role, content, api_content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, HISTORY_MESSAGES),
        ).fetchall()[::-1]
        while rows and rows[0]["role"] != "user":
            rows = rows[1:]
        history = []
        for row in rows:
            text = row["api_content"] or row["content"]
            if history and history[-1]["role"] == row["role"]:
                history[-1]["content"] += "\n\n" + text  # keep strict user/assistant alternation
            else:
                history.append({"role": row["role"], "content": text})
        return history

    # ------------------------------------------------------------------ main entry

    def answer(self, conn, user, question: str, mode: str, subject: str | None,
               language: str, conversation_id: int | None, image: dict | None = None) -> Iterator[dict]:
        if conversation_id:
            convo = conn.execute(
                "SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user["id"])
            ).fetchone()
            if convo is None:
                raise ValueError("Conversation not found")
            mode, subject = convo["mode"], convo["subject"]  # a conversation keeps its original scope
            try:
                docs, scope = self.resolve_scope(conn, mode, subject)
            except ValueError:
                if mode != "subject":
                    raise
                # The subject's notes were deleted since; carry on with all the notes instead.
                docs, scope = self.resolve_scope(conn, "subject", "all")
        else:
            docs, scope = self.resolve_scope(conn, mode, subject)
            title = question.strip().replace("\n", " ")
            title = title[:60] + ("…" if len(title) > 60 else "")
            cur = conn.execute(
                "INSERT INTO conversations (user_id, mode, subject, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user["id"], mode, scope, title, now_iso(), now_iso()),
            )
            conversation_id = cur.lastrowid
            conn.commit()
        history = self.load_history(conn, conversation_id)
        api_question = self.student_context(user, language) + "\n\n"
        text, engine, sources, suggestions = "", "library", [], []
        counts = True  # whether this question earns XP and counts towards the daily goal
        saved = False

        def save() -> dict | None:
            """Store the question and the answer so far. Runs once, also when the student stops the
            answer or the connection drops part-way (then the reply is kept as far as it got)."""
            nonlocal saved
            if saved:
                return None
            saved = True
            asked_row = conn.execute(
                "INSERT INTO messages (conversation_id, role, content, api_content, language, created_at) VALUES (?, 'user', ?, ?, ?, ?)",
                # The photo itself isn't kept; the saved question notes that one was attached.
                (conversation_id, f"{PHOTO_MARK}{question}" if image else question,
                 (api_question + "\n\n(The student attached a photo with this question.)" if image else api_question)
                 if engine == "ai" else None, language, now_iso()),
            )
            answer_id = None
            if text.strip():
                cur = conn.execute(
                    """INSERT INTO messages (conversation_id, role, content, language, engine, suggestions, created_at)
                       VALUES (?, 'assistant', ?, ?, ?, ?, ?)""",
                    (conversation_id, text, language, engine, json.dumps(suggestions, ensure_ascii=False), now_iso()),
                )
                answer_id = cur.lastrowid
            conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now_iso(), conversation_id))
            reward = gamification.record_question(conn, user["id"], mode, scope if scope != "all" else None, language) if counts else None
            conn.commit()
            return {"user_message_id": asked_row.lastrowid, "message_id": answer_id, "reward": reward}

        try:
            yield {"type": "start", "conversation_id": conversation_id}

            system, inlined = self.build_system(mode, docs)
            if not inlined:
                api_question += self.retrieved_notes(conn, question, docs)
            api_question += question

            asked = [m["content"] for m in self._asked(conn, conversation_id)] + [question]
            ai_attempted = self.ai.available
            if ai_attempted:
                try:
                    chunks = []
                    splitter = followups.FollowupSplitter()
                    asking = {"role": "user", "content": api_question, **({"image": image} if image else {})}
                    engine = "ai"  # so a stopped answer is saved with the prompt it was given
                    for kind, value in self.ai.stream_reply(system, history + [asking]):
                        if kind == "text":
                            visible = splitter.feed(value)
                            if visible:
                                chunks.append(visible)
                                text = "".join(chunks)
                                yield {"type": "delta", "text": visible}
                    rest, block = splitter.finish()
                    if rest:
                        chunks.append(rest)
                        yield {"type": "delta", "text": rest}
                    # Drop a stray closing divider some models write before the follow-up marker.
                    text = re.sub(r"\n\s*(?:-{3,}|\*{3,})\s*$", "", "".join(chunks).strip()).strip()
                    suggestions = followups.parse(block, asked)
                except ImagesUnsupported as exc:
                    text, engine, counts = str(exc), "library", False
                    yield {"type": "replace", "text": text}
                except AIUnavailable as exc:
                    log.warning("Falling back to library answer: %s", exc)
                    text, engine = "", "library"
            if not text.strip() and image:
                text, counts = ("Questions with a picture need the AI tutor, which isn't available right now. "
                                "Please type the question instead and I'll answer from the study notes."), False
                yield {"type": "replace", "text": text}
            if not text.strip():
                text, sources = self.library_answer(conn, question, mode, docs, language)
                if ai_attempted:
                    text += "\n\n_(The AI tutor is unavailable right now, so this answer comes from the study notes.)_"
                yield {"type": "replace", "text": text}
            if len(suggestions) < 2:
                suggestions = self.note_suggestions(conn, question, mode, docs, language, asked)
        except GeneratorExit:
            # Stopped by the student, or the connection dropped: keep the question and the partial answer.
            if text.strip():
                text = text.rstrip() + "\n\n_(Stopped before the answer was finished.)_"
            suggestions = []
            try:
                save()
            except Exception:
                log.exception("Couldn't save a stopped answer")
            raise
        except Exception:
            # Something unexpected broke the answer: keep at least the question, then report the error.
            counts = False
            try:
                save()
            except Exception:
                log.exception("Couldn't save the question after a failed answer")
            raise

        stored = save()
        reward = stored["reward"] or {"level_up": None, "xp": 0, "badges": [],
                                      "goal": {**gamification.daily_goal_status(conn, user["id"]), "reached_now": False, "bonus_xp": 0}}
        xp_total = conn.execute("SELECT xp FROM users WHERE id = ?", (user["id"],)).fetchone()["xp"]

        yield {
            "type": "done",
            "message_id": stored["message_id"],
            "user_message_id": stored["user_message_id"],
            "engine": engine,
            "sources": sources,
            "suggestions": suggestions,
            "level_up": reward["level_up"],
            "goal": reward["goal"],
            "xp_gained": reward["xp"],
            "badges": reward["badges"],
            "progress": gamification.level_info(xp_total),
        }
