"""A ready-made demo school for presenting TatvaX.

    python run.py --demo          start TatvaX with the demo school (created on first use)
    python run.py --demo-reset    rebuild the demo school first, so streaks and due dates are current
    python -m tatvax.demo         just build it (add --reset to rebuild)

Everything lives in its own folder (instance-demo/), never in the real instance/ folder. The school
is fictional: Sunrise Public School, with a principal, an admin, teachers, a teaching assistant and
students in classes 6 to 10 who have been learning for the past month in many languages. Every
account's password is DEMO_PASSWORD; the list is written to instance-demo/DEMO_ACCOUNTS.txt.
"""

import argparse
import json
import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from flask import Blueprint, current_app, request, session
from werkzeug.security import generate_password_hash

DEMO_PASSWORD = "tatvax-demo"
SCHOOL = "Sunrise Public School"
DAYS = 30  # how much history to make
DEFAULT_DIR = Path(__file__).resolve().parent.parent / "instance-demo"

# The role ladder, top to bottom (Owner at the top and Student at the bottom are built in).
CUSTOM_ROLES = [
    # name, colour, position, permissions
    ("Head of Department", "#7c3aed", 4, ["manage_roles", "manage_content", "manage_assignments", "view_students",
                                          "view_analytics", "view_feedback"]),
    ("Content Editor", "#2563eb", 2, ["manage_content"]),
    ("Class Monitor", "#ca8a04", 1, ["view_analytics"]),
]
BUILT_IN_POSITIONS = {"admin": 5, "teacher": 3}

# name, email, roles, title (shown in DEMO_ACCOUNTS.txt)
STAFF = [
    ("Dr. Meera Iyer", "principal@sunrise.school", ["owner"], "Principal: every permission"),
    ("Arjun Mehta", "admin@sunrise.school", ["admin"], "School office and IT: administrator"),
    ("Kavita Sharma", "kavita.sharma@sunrise.school", ["Head of Department", "teacher"], "Head of Science"),
    ("Rahul Verma", "rahul.verma@sunrise.school", ["teacher"], "Mathematics teacher"),
    ("Fatima Sheikh", "fatima.sheikh@sunrise.school", ["teacher"], "English teacher"),
    ("Joseph D'Souza", "joseph.dsouza@sunrise.school", ["teacher"], "Social Studies teacher"),
    ("Neha Kulkarni", "neha.kulkarni@sunrise.school", ["Content Editor"], "Teaching assistant: edits the study notes"),
]

# name, email, class, language, learner type, extra roles
STUDENTS = [
    ("Aarav Patel", "aarav@sunrise.school", 8, "en", "star", []),  # English, so evaluators can follow along
    ("Ananya Reddy", "ananya@sunrise.school", 8, "te", "steady", []),
    ("Ishaan Gupta", "ishaan@sunrise.school", 8, "hi", "struggling", []),
    ("Kiran Rao", "kiran@sunrise.school", 8, "en", "steady", ["Class Monitor"]),
    ("Diya Nair", "diya@sunrise.school", 9, "ml", "star", []),
    ("Kabir Singh", "kabir@sunrise.school", 9, "pa", "steady", []),
    ("Meenakshi Sundaram", "meenakshi@sunrise.school", 9, "ta", "steady", []),
    ("Priya Chatterjee", "priya@sunrise.school", 9, "bn", "new", []),
    ("Rohan Das", "rohan@sunrise.school", 10, "bn", "star", []),
    ("Sneha Kulkarni", "sneha@sunrise.school", 10, "mr", "steady", []),
    ("Aditi Bose", "aditi@sunrise.school", 10, "as", "struggling", []),
    ("Vihaan Joshi", "vihaan@sunrise.school", 7, "hi", "new", []),
    ("Zara Khan", "zara@sunrise.school", 7, "ur", "steady", []),
    ("Siddharth Menon", "siddharth@sunrise.school", 7, "ml", "struggling", []),
    ("Arnav Mishra", "arnav@sunrise.school", 6, "hi", "star", []),
    ("Riya Thomas", "riya@sunrise.school", 6, "en", "steady", []),
]

# How each kind of learner behaves: share of days active, current streak, answer accuracy,
# questions per active day, chance of an assessment on an active day.
PROFILES = {
    "star": {"active": 0.85, "streak": 12, "accuracy": 0.86, "questions": (2, 5), "quiz": 0.45, "goal": 6},
    "steady": {"active": 0.55, "streak": 3, "accuracy": 0.68, "questions": (1, 4), "quiz": 0.3, "goal": 5},
    "struggling": {"active": 0.3, "streak": 0, "accuracy": 0.45, "questions": (1, 3), "quiz": 0.25, "goal": 3},
    "new": {"active": 1.0, "streak": 3, "accuracy": 0.62, "questions": (1, 3), "quiz": 0.4, "goal": 4, "days": 4},
}

QUESTIONS = {
    "mathematics": ["What is the BODMAS rule?", "How do I add fractions with different denominators?",
                    "How do I convert a fraction into a decimal?", "How do I find 15% of a number?",
                    "What is a variable in algebra?", "How do I find the area of a rectangle?",
                    "What is the difference between prime and composite numbers?", "How do I find the mean of data?",
                    "What are the types of angles?", "How do I solve a simple equation like 2x + 3 = 11?"],
    "science": ["What are the three states of matter?", "What is photosynthesis?", "How does sound travel?",
                "What is the water cycle?", "What are Newton's laws of motion?", "How do we see objects?",
                "What is the difference between conduction and convection?", "What are the parts of a plant?",
                "How does the human heart work?", "Why is the environment important?"],
    "english": ["What are the parts of speech?", "When do I use the present perfect tense?",
                "How do I use commas correctly?", "What is the difference between a phrase and a clause?",
                "How can I improve my vocabulary?", "How do I write a good paragraph?",
                "What is a metaphor?", "How do I answer reading comprehension questions?"],
    "social-studies": ["Who started the Non-Cooperation Movement?", "What were the main features of the Indus Valley Civilisation?",
                       "What are the Fundamental Rights?", "What are the major rivers of India?",
                       "How does the Indian Parliament work?", "What were the achievements of the Mughal Empire?",
                       "What is the difference between weather and climate?", "What are our duties as citizens?"],
}
HELPDESK_QUESTIONS = ["What are the school timings?", "How do I pay the school fees?", "When are the half-yearly exams?",
                      "What facilities does the school have?", "What is the uniform policy?", "How can parents meet teachers?"]

# Conversations in students' own languages, as the AI tutor would answer them (each language's
# chats are used in turn by the students who speak it).
NATIVE_CHATS = {
    "hi": [("science", "प्रकाश संश्लेषण क्या है?",
           "**प्रकाश संश्लेषण** (photosynthesis) वह प्रक्रिया है जिसमें हरे पौधे सूर्य के प्रकाश की मदद से अपना भोजन बनाते हैं।\n\n"
           "1. पत्तियाँ हवा से **कार्बन डाइऑक्साइड** लेती हैं।\n2. जड़ें मिट्टी से **पानी** सोखती हैं।\n"
           "3. पत्तियों में मौजूद **क्लोरोफिल** सूर्य का प्रकाश पकड़ता है।\n4. इनसे पौधा **ग्लूकोज़** (भोजन) बनाता है और **ऑक्सीजन** छोड़ता है।\n\n"
           "$$6CO_2 + 6H_2O \\rightarrow C_6H_{12}O_6 + 6O_2$$\n\nअभ्यास प्रश्न: पौधे का कौन-सा भाग प्रकाश संश्लेषण करता है?"),
           ("mathematics", "भिन्न क्या होती है?",
            "**भिन्न** (fraction) किसी पूरी चीज़ के बराबर हिस्सों को दिखाती है। अगर एक रोटी के 4 बराबर टुकड़े करें और "
            "उनमें से 1 टुकड़ा लें, तो वह $\\frac{1}{4}$ है।\n\n"
            "- ऊपर की संख्या **अंश** (numerator) है: कितने हिस्से लिए गए।\n"
            "- नीचे की संख्या **हर** (denominator) है: कुल कितने बराबर हिस्से हैं।\n\n"
            "अभ्यास प्रश्न: 8 में से 3 टुकड़े खाने पर कौन-सी भिन्न बनेगी?")],
    "ta": [("mathematics", "1/2 மற்றும் 1/3 ஐ எப்படி கூட்டுவது?",
           "வெவ்வேறு பகுதிகள் (denominators) உள்ள பின்னங்களைக் கூட்ட, முதலில் பொதுப் பகுதியைக் கண்டுபிடிக்க வேண்டும்.\n\n"
           "1. 2 மற்றும் 3 இன் மீ.சி.ம (LCM) = **6**\n2. $\\frac{1}{2} = \\frac{3}{6}$, $\\frac{1}{3} = \\frac{2}{6}$\n"
           "3. $\\frac{3}{6} + \\frac{2}{6} = \\frac{5}{6}$\n\nவிடை: **5/6**. பயிற்சி: $\\frac{1}{4} + \\frac{1}{2}$ = ?")],
    "bn": [("science", "জলচক্র কী?",
           "**জলচক্র** (water cycle) হলো পৃথিবীতে জলের অবিরাম চলাচলের প্রক্রিয়া।\n\n"
           "1. **বাষ্পীভবন**: সূর্যের তাপে নদী ও সমুদ্রের জল বাষ্প হয়ে ওপরে ওঠে।\n"
           "2. **ঘনীভবন**: ঠান্ডা বাতাসে বাষ্প জমে মেঘ তৈরি করে।\n3. **বৃষ্টিপাত**: মেঘ থেকে বৃষ্টি বা তুষার হয়ে জল নেমে আসে।\n"
           "4. **সংগ্রহ**: জল আবার নদী, হ্রদ ও সমুদ্রে ফিরে যায়।\n\nবর্ষাকালের বৃষ্টিও এই জলচক্রেরই অংশ!")],
}

TODOS = [
    # title, subject, priority, due (days from today, None for no date), tags, subtasks, done
    ("Revise Chapter 4: Fractions", "mathematics", "high", 1, ["revision", "unit test"], ["Re-read the notes", "Do 10 practice sums"], False),
    ("Finish the science worksheet on light", "science", "medium", 0, ["homework"], [], False),
    ("Learn 10 new vocabulary words", "english", "low", 3, ["vocabulary"], ["Words 1-5", "Words 6-10"], False),
    ("Make notes on the freedom struggle", "social-studies", "medium", -1, ["notes"], [], False),
    ("Practise tenses exercise", "english", "medium", 5, ["grammar"], [], False),
    ("Read the water cycle chapter", "science", "low", -3, ["reading"], [], True),
    ("Complete the algebra practice set", "mathematics", "urgent", 0, ["homework"], ["Questions 1-10", "Questions 11-20"], False),
    ("Prepare for the half-yearly exams", None, "high", 12, ["exams"], ["Make a timetable", "Collect past papers"], False),
]
STAFF_TODOS = [
    ("Prepare the Class 8 unit test", "mathematics", "high", 2, ["planning"]),
    ("Update the science notes for Chapter 5: Light", "science", "medium", 4, ["notes"]),
    ("Check Class 9 grammar assignment results", "english", "medium", 1, ["marking"]),
    ("Plan the parent-teacher meeting", None, "high", 6, ["meeting"]),
]

FEEDBACK = [
    (5, "Ananya Reddy (parent)", "My daughter asks TatvaX questions in Telugu every evening. The step-by-step answers really help."),
    (4, "Rohan Das", "The timed assessments are great practice before exams. Please add more history questions!"),
    (5, "Diya Nair", "I love the review deck. The questions I got wrong keep coming back until I remember them."),
    (3, None, "Voice input sometimes doesn't understand me when the classroom is noisy."),
    (4, "Kabir Singh", "The translator is very useful for understanding English words in Punjabi."),
    (5, "Mrs. Reddy (parent)", "The progress report PDF made the parent-teacher meeting much easier."),
]


# --------------------------------------------------------------------------- helpers

def _when(days_ago: int, hour: int, minute: int = 0) -> datetime:
    from .db import SCHOOL_TZ

    now = datetime.now(SCHOOL_TZ)
    moment = (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    latest = now - timedelta(minutes=90)  # today's activity happened earlier today, never in the future
    if moment > latest:
        moment = max(latest, now.replace(hour=0, minute=1, second=0, microsecond=0))
    return moment


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def _chapters(conn, slug: str) -> list[str]:
    body = conn.execute("SELECT body FROM documents WHERE slug = ?", (slug,)).fetchone()["body"]
    return [line[3:].strip() for line in body.splitlines() if line.startswith("## Chapter")]


class _School:
    """Builds the demo school inside an app context, one piece at a time."""

    def __init__(self, app, conn, rng: random.Random):
        from . import roles

        self.app, self.conn, self.rng, self.roles = app, conn, rng, roles
        self.services = app.extensions["tatvax"]
        self.password = generate_password_hash(DEMO_PASSWORD)
        self.people: dict[str, int] = {}
        self.answers: dict[tuple, tuple] = {}

    # ------------------------------------------------------------ roles and people

    def make_roles(self):
        conn = self.conn
        for key, position in BUILT_IN_POSITIONS.items():
            conn.execute("UPDATE roles SET position = ? WHERE key = ?", (position, key))
        for name, color, position, permissions in CUSTOM_ROLES:
            conn.execute("INSERT INTO roles (name, color, position, permissions, created_at) VALUES (?, ?, ?, ?, ?)",
                         (name, color, position, json.dumps(permissions), _iso(_when(DAYS + 5, 9))))

    def role(self, name: str) -> int:
        row = self.conn.execute("SELECT id FROM roles WHERE key = ? OR name = ?", (name, name)).fetchone()
        return row["id"]

    def add_person(self, name, email, joined_days_ago, grade=None, language="en", goal=5, leaderboard=1):
        cur = self.conn.execute(
            """INSERT INTO users (name, email, password_hash, role, is_guest, language, grade, leaderboard, daily_goal,
                                  created_at, last_seen) VALUES (?, ?, ?, 'student', 0, ?, ?, ?, ?, ?, ?)""",
            (name, email, self.password, language, grade, leaderboard, goal, _iso(_when(joined_days_ago, 8)), _iso(_when(0, 8))),
        )
        self.people[name] = cur.lastrowid
        return cur.lastrowid

    def make_people(self):
        for i, (name, email, role_names, _title) in enumerate(STAFF):
            uid = self.add_person(name, email, DAYS + 10 - i)
            for role_name in role_names:
                self.roles.assign(self.conn, uid, self.role(role_name))
        for name, email, grade, language, kind, extra in STUDENTS:
            profile = PROFILES[kind]
            joined = profile.get("days", DAYS) + 2
            uid = self.add_person(name, email, joined, grade, language, profile["goal"],
                                  leaderboard=0 if name == "Siddharth Menon" else 1)  # one learner opted out
            for role_name in extra:
                self.roles.assign(self.conn, uid, self.role(role_name))
        # A few visitors who never made an account.
        for _ in range(5):
            self.conn.execute("INSERT INTO users (name, is_guest, created_at, last_seen) VALUES ('Learner', 1, ?, ?)",
                              (_iso(_when(self.rng.randint(0, 10), 11)), _iso(_when(0, 11))))

    # ------------------------------------------------------------ rewards (the app's own rules)

    def xp(self, uid, reason, points, moment):
        self.conn.execute("INSERT INTO xp_events (user_id, reason, points, created_at) VALUES (?, ?, ?, ?)",
                          (uid, reason, points, _iso(moment)))

    def touch(self, uid, day: str, moment, questions=0, quizzes=0, goal=5):
        """Record activity for a day, with the daily bonus and the daily-goal bonus as the app gives them."""
        conn = self.conn
        row = conn.execute("SELECT questions, quizzes FROM activity WHERE user_id = ? AND day = ?", (uid, day)).fetchone()
        if row is None:
            self.xp(uid, "daily_bonus", 10, moment)
            before = 0
        else:
            before = row["questions"] + row["quizzes"]
        conn.execute(
            """INSERT INTO activity (user_id, day, questions, quizzes) VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, day) DO UPDATE SET questions = questions + excluded.questions, quizzes = quizzes + excluded.quizzes""",
            (uid, day, questions, quizzes))
        if before < goal <= before + questions + quizzes:
            self.xp(uid, "daily_goal", 15, moment)

    # ------------------------------------------------------------ questions

    def answer(self, question: str, mode: str, subject: str):
        key = (question, mode, subject)
        if key not in self.answers:
            tutor = self.services.tutor
            docs, scope = tutor.resolve_scope(self.conn, mode, subject if mode == "subject" else None)
            text, sources = tutor.library_answer(self.conn, question, mode, docs, "en")
            from . import followups

            suggestions = followups.from_notes(self.conn, question, [d["slug"] for d in docs], mode, [question])
            self.answers[key] = (text, sources, suggestions, scope)
        return self.answers[key]

    def conversation(self, uid, mode, subject, turns, moment, language="en", engine="library"):
        """Store a chat: turns is a list of (question, answer or None to use the notes)."""
        conn = self.conn
        title = turns[0][0][:60]
        cur = conn.execute(
            "INSERT INTO conversations (user_id, mode, subject, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (uid, mode, subject, title, _iso(moment), _iso(moment)))
        cid = cur.lastrowid
        for question, written in turns:
            if written is None:
                text, _sources, suggestions, _scope = self.answer(question, mode, subject)
                answer_engine = "library"
            else:
                text, suggestions, answer_engine = written, [], engine
            conn.execute("INSERT INTO messages (conversation_id, role, content, language, created_at) VALUES (?, 'user', ?, ?, ?)",
                         (cid, question, language, _iso(moment)))
            moment += timedelta(seconds=self.rng.randint(4, 15))
            conn.execute(
                """INSERT INTO messages (conversation_id, role, content, language, engine, suggestions, created_at)
                   VALUES (?, 'assistant', ?, ?, ?, ?, ?)""",
                (cid, text, language, answer_engine, json.dumps(suggestions, ensure_ascii=False), _iso(moment)))
            conn.execute("INSERT INTO question_log (user_id, mode, subject, language, created_at) VALUES (?, ?, ?, ?, ?)",
                         (uid, mode, subject if subject != "all" else None, language, _iso(moment)))
            moment += timedelta(minutes=self.rng.randint(1, 6))
        conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (_iso(moment), cid))
        return moment

    # ------------------------------------------------------------ assessments

    def take_quiz(self, uid, questions, accuracy, moment, mode="practice", topic=None, assignment_id=None,
                  finish=True, engine="library"):
        from .quiz import SECONDS_PER_QUESTION

        conn, rng = self.conn, self.rng
        slugs = list(dict.fromkeys(q["subject"] for q in questions))
        time_limit = SECONDS_PER_QUESTION["medium"] * len(questions) if mode == "timed" else None
        answers = {}
        for i, q in enumerate(questions):
            if not finish and i >= len(questions) // 2:
                break
            if rng.random() < accuracy:
                answers[str(i)] = q["answer_index"]
            elif mode != "practice" and rng.random() < 0.12:
                continue  # left blank in an exam
            else:
                answers[str(i)] = rng.choice([c for c in range(4) if c != q["answer_index"]])
        if mode != "practice" and not finish:
            answers = {}
        score = sum(1 for i, q in enumerate(questions) if answers.get(str(i)) == q["answer_index"])
        duration = len(questions) * rng.randint(25, 55)
        if time_limit:
            duration = min(duration, time_limit - rng.randint(5, 60))
        completed = moment + timedelta(seconds=duration) if finish else None
        cur = conn.execute(
            """INSERT INTO quizzes (user_id, subject, subjects_json, topic, language, difficulty, questions_json, answers_json,
                                    score, total, engine, mode, time_limit, duration_s, assignment_id, created_at, completed_at)
               VALUES (?, ?, ?, ?, 'en', 'medium', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (uid, slugs[0] if len(slugs) == 1 else "mixed", json.dumps(slugs), topic, json.dumps(questions, ensure_ascii=False),
             json.dumps(answers), score if finish else None, len(questions), engine, mode, time_limit,
             duration if finish else None, assignment_id, _iso(moment), _iso(completed) if completed else None))
        if finish:
            from . import review

            review.add_missed(conn, uid, questions, answers)
            points = 10 + 5 * score
            self.xp(uid, "quiz", points, completed)
            if len(questions) >= 5 and score == len(questions):
                self.xp(uid, "perfect_quiz", 20, completed)
            if mode == "timed" and score / len(questions) >= 0.8:
                self.xp(uid, "timed_bonus", 10, completed)
        return cur.lastrowid, score, completed

    def bank(self, slug, count):
        questions = self.services.quizmaster._generate_offline(slug, "", count, "mixed")
        title = self.conn.execute("SELECT title FROM documents WHERE slug = ?", (slug,)).fetchone()["title"]
        return [{**q, "subject": slug, "subject_title": title} for q in questions]

    # ------------------------------------------------------------ a month of learning

    def learning_history(self):
        conn, rng = self.conn, self.rng
        subjects = list(QUESTIONS)
        for name, _email, grade, language, kind, _extra in STUDENTS:
            uid, profile = self.people[name], PROFILES[kind]
            span = profile.get("days", DAYS)
            favourite = rng.choice(subjects)
            streak = profile["streak"]
            days = [d for d in range(span) if d < streak or (d != streak and rng.random() < profile["active"])]
            if streak == 0:
                days = [d for d in days if d >= 2]  # broke their streak recently
            native = list(NATIVE_CHATS.get(language, []))  # chats in their own language, one per day
            for days_ago in sorted(days, reverse=True):
                day = _when(days_ago, 12).date().isoformat()
                moment = _when(days_ago, rng.choice([7, 16, 17, 18, 19, 20]), rng.randint(0, 59))
                count = rng.randint(*profile["questions"])
                subject = favourite if rng.random() < 0.5 else rng.choice(subjects)
                pool = QUESTIONS[subject][:]
                rng.shuffle(pool)
                asked = 0
                if native and days_ago < 14:
                    native_subject, question, written = native.pop(0)
                    moment = self.conversation(uid, "subject", native_subject, [(question, written)], moment, language, engine="ai")
                    asked += 1
                turns = [(q, None) for q in pool[:max(0, count - asked)]]
                if turns:
                    moment = self.conversation(uid, "subject", subject, turns, moment)
                    asked += len(turns)
                if rng.random() < 0.08:
                    moment = self.conversation(uid, "helpdesk", "school-faq", [(rng.choice(HELPDESK_QUESTIONS), None)], moment)
                    asked += 1
                # XP for questions, at most 100 a day, as the app gives it.
                for _ in range(min(asked, 20)):
                    self.xp(uid, "question", 5, moment)
                quizzes = 0
                if rng.random() < profile["quiz"]:
                    mode = rng.choices(["practice", "exam", "timed"], [0.5, 0.3, 0.2])[0]
                    if rng.random() < 0.2:
                        questions = self.bank(subject, 3) + self.bank(rng.choice([s for s in subjects if s != subject]), 3)
                        rng.shuffle(questions)
                    else:
                        questions = self.bank(subject, rng.choice([5, 5, 10]))
                    self.take_quiz(uid, questions, profile["accuracy"], moment + timedelta(minutes=10), mode)
                    quizzes = 1
                self.touch(uid, day, moment, questions=asked, quizzes=quizzes, goal=profile["goal"])
            # One unfinished assessment to show "Continue" in the history.
            if kind in ("steady", "struggling"):
                self.take_quiz(uid, self.bank(favourite, 5), profile["accuracy"], _when(1, 18), "practice", finish=False)

    def review_deck(self):
        """Learners have worked through part of their review deck."""
        from .review import INTERVALS

        conn, rng = self.conn, self.rng
        today = _when(0, 12).date()
        for name, _email, _grade, _language, kind, _extra in STUDENTS:
            uid = self.people[name]
            skill = PROFILES[kind]["accuracy"]
            for card in conn.execute("SELECT id FROM review_cards WHERE user_id = ?", (uid,)).fetchall():
                roll = rng.random()
                if roll < 0.35:  # due now
                    box, due, reviews = rng.choice([0, 0, 1]), today - timedelta(days=rng.randint(0, 2)), rng.randint(0, 2)
                elif roll < 0.35 + skill * 0.25:  # mastered
                    box, due, reviews = 5, today + timedelta(days=INTERVALS[5]), rng.randint(5, 8)
                else:  # learning, back in a few days
                    box = rng.randint(1, 4)
                    due, reviews = today + timedelta(days=rng.randint(1, INTERVALS[box])), box + rng.randint(0, 2)
                conn.execute("UPDATE review_cards SET box = ?, due = ?, reviews = ?, lapses = ?, reviewed_at = ? WHERE id = ?",
                             (box, due.isoformat(), reviews, rng.randint(0, 2) if reviews else 0,
                              _iso(_when(rng.randint(0, 6), 19)) if reviews else None, card["id"]))
                if reviews and box:
                    self.xp(uid, "review", 2, _when(rng.randint(0, 6), 19))

    # ------------------------------------------------------------ teachers' work

    def assignments(self):
        conn, rng, quizmaster = self.conn, self.rng, self.services.quizmaster
        chapter = {slug: _chapters(conn, slug) for slug in QUESTIONS}

        def find(slug, word):
            return next((c for c in chapter[slug] if word.lower() in c.lower()), chapter[slug][0])

        plan = [
            # teacher, title, kind, subject, chapter word, class, mode, count, due (days), created (days ago), archived
            ("Rahul Verma", "Fractions practice before the unit test", "quiz", "mathematics", "Fractions", 8, "exam", 10, 3, 4, False),
            ("Kavita Sharma", "Read: Water and the water cycle", "reading", "science", "Water", None, "practice", 0, -1, 6, False),
            ("Fatima Sheikh", "Grammar check: tenses", "quiz", "english", "Tenses", 9, "practice", 5, 6, 2, False),
            ("Joseph D'Souza", "Freedom struggle revision", "quiz", "social-studies", "Freedom", 10, "timed", 8, 5, 3, False),
            ("Kavita Sharma", "Light: reflection and shadows", "quiz", "science", "Light", None, "practice", 5, 9, 1, False),
            ("Rahul Verma", "Algebra basics", "quiz", "mathematics", "Algebra", 8, "practice", 5, -12, 18, True),
        ]
        for teacher, title, kind, slug, word, grade, mode, count, due, created, archived in plan:
            topic = find(slug, word)
            questions_json, engine = None, None
            if kind == "quiz":
                made = quizmaster.generate(conn, [slug], "", count, "mixed", "en")
                questions_json, engine = json.dumps(made["questions"], ensure_ascii=False), made["engine"]
            due_date = _when(0, 12).date() + timedelta(days=due)
            cur = conn.execute(
                """INSERT INTO assignments (teacher_id, title, instructions, kind, subjects_json, topic, grade, mode, difficulty,
                                            language, questions_json, engine, due_date, archived, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'mixed', 'en', ?, ?, ?, ?, ?)""",
                (self.people[teacher], title, f"Please finish this before {due_date.strftime('%d %B')}. Ask TatvaX if you get stuck!",
                 kind, json.dumps([slug]), topic, grade, mode, questions_json, engine, due_date.isoformat(),
                 1 if archived else 0, _iso(_when(created, 9))))
            aid = cur.lastrowid
            # Which students see it, and who has done it.
            for name, _email, s_grade, _language, s_kind, _extra in STUDENTS:
                if grade and s_grade != grade:
                    continue
                uid, skill = self.people[name], PROFILES[s_kind]["accuracy"]
                chance = {"star": 0.95, "steady": 0.7, "struggling": 0.35, "new": 0.5}[s_kind]
                if rng.random() > chance:
                    continue
                days_ago = rng.randint(max(0, created - 6), created) if created else 0
                moment = _when(min(days_ago, created), 18, rng.randint(0, 59))
                if kind == "reading":
                    conn.execute("INSERT INTO assignment_done (assignment_id, user_id, completed_at) VALUES (?, ?, ?)",
                                 (aid, uid, _iso(moment)))
                    continue
                from .quiz import _shuffle_options

                questions = [_shuffle_options(q) for q in json.loads(questions_json)]
                rng.shuffle(questions)
                finish = rng.random() > 0.15
                self.take_quiz(uid, questions, skill, moment, mode, topic=title, assignment_id=aid, finish=finish, engine=engine)
                if finish and rng.random() < 0.25:  # a second try to improve
                    self.take_quiz(uid, questions, min(0.98, skill + 0.2), moment + timedelta(hours=2), mode, topic=title,
                                   assignment_id=aid, engine=engine)

    def todos(self):
        conn, rng = self.conn, self.rng
        today = _when(0, 12).date()

        def add(uid, title, subject, priority, due, tags, subtasks, done, position):
            moment = _when(rng.randint(1, 10), 17)
            conn.execute(
                """INSERT INTO todos (user_id, title, notes, done, priority, due_date, subject, tags, subtasks, link, position,
                                      created_at, updated_at, completed_at) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (uid, title, 1 if done else 0, priority, (today + timedelta(days=due)).isoformat() if due is not None else None,
                 subject, json.dumps(tags), json.dumps([{"text": s, "done": done or rng.random() < 0.4} for s in subtasks]),
                 f"/notes/{subject}" if subject else None, position, _iso(moment), _iso(moment), _iso(moment) if done else None))

        for name, *_rest in STUDENTS:
            for position, item in enumerate(rng.sample(TODOS, rng.randint(3, 6))):
                add(self.people[name], *item, position)
        for name in ("Rahul Verma", "Kavita Sharma", "Fatima Sheikh", "Joseph D'Souza"):
            for position, (title, subject, priority, due, tags) in enumerate(rng.sample(STAFF_TODOS, 3)):
                add(self.people[name], title, subject, priority, due, tags, [], False, position)

    def reading_and_feedback(self):
        conn, rng = self.conn, self.rng
        for name, _email, _grade, _language, kind, _extra in STUDENTS:
            uid = self.people[name]
            for slug in QUESTIONS:
                read = rng.sample(range(len(_chapters(conn, slug))), k=int(len(_chapters(conn, slug)) * PROFILES[kind]["accuracy"] * rng.random()))
                conn.executemany("INSERT INTO notes_read (user_id, slug, chapter, read_at) VALUES (?, ?, ?, ?)",
                                 [(uid, slug, f"ch-{i}", _iso(_when(rng.randint(0, DAYS), 20))) for i in read])
        for rating, who, message in FEEDBACK:
            uid = self.people.get((who or "").replace(" (parent)", ""))
            conn.execute("INSERT INTO feedback (user_id, rating, name, email, message, page, created_at) VALUES (?, ?, ?, NULL, ?, ?, ?)",
                         (uid, rating, who, message, rng.choice(["/", "/learn/science", "/assessments", "/review"]),
                          _iso(_when(rng.randint(0, 14), 21))))

    def finish(self):
        """Totals and achievements, worked out exactly as the app does."""
        from . import gamification

        conn, rng = self.conn, self.rng
        conn.execute("UPDATE users SET xp = (SELECT COALESCE(SUM(points), 0) FROM xp_events WHERE xp_events.user_id = users.id)")
        for uid in self.people.values():
            for badge in gamification.check_badges(conn, uid):
                conn.execute("UPDATE badges SET earned_at = ? WHERE user_id = ? AND badge = ?",
                             (_iso(_when(rng.randint(0, 20), 19)), uid, badge["id"]))
        self.roles.refresh_cache(conn)


# --------------------------------------------------------------------------- one-click switching

# The accounts shown in the demo bar, each with the features worth showing for it. Everyone else
# in the school stays in the background (classmates on the leaderboard, in class lists and so on).
PERSONAS = [
    {"key": "principal", "email": "principal@sunrise.school", "label": "Principal", "role": "Owner",
     "summary": "Runs the school: every permission, including roles and AI settings.", "start": "/teacher/overview",
     "tour": [["Class analytics", "/teacher/overview"], ["Roles and permissions", "/teacher/roles"],
              ["AI provider settings", "/teacher/ai"], ["Study-notes editor", "/teacher/content"],
              ["Students and PDF reports", "/teacher/students"], ["Parent and student feedback", "/teacher/feedback"]]},
    {"key": "teacher", "email": "rahul.verma@sunrise.school", "label": "Teacher", "role": "Teacher",
     "summary": "Mathematics. Sets work and follows the class, but has no AI settings or Roles tab.",
     "start": "/teacher/assignments",
     "tour": [["Assignments and who has finished", "/teacher/assignments"], ["Students and PDF reports", "/teacher/students"],
              ["Edit the study notes", "/teacher/content"], ["Class analytics", "/teacher/overview"]]},
    {"key": "monitor", "email": "kiran@sunrise.school", "label": "Class Monitor", "role": "Student + Class Monitor",
     "summary": "Class 8. A student whose extra role opens the class analytics, and nothing more.",
     "start": "/teacher/overview",
     "tour": [["Class analytics (from the role)", "/teacher/overview"], ["Their own overview", "/"],
              ["Assignments for Class 8", "/assignments"], ["Progress and leaderboard", "/progress"]]},
    {"key": "star", "email": "aarav@sunrise.school", "label": "Star student", "role": "Student",
     "summary": "Class 8. A 12-day streak, near the top of the leaderboard.", "start": "/",
     "tour": [["Daily goal and “For today”", "/"], ["Ask the tutor", "/learn/mathematics"],
              ["Take an assessment", "/assessments"], ["Assessment history", "/assessments/history"],
              ["Review deck", "/review"], ["Badges, streak and leaderboard", "/progress"],
              ["Teacher's assignments", "/assignments"], ["Study notes", "/notes/science"], ["To-do list", "/todos"],
              ["Translator", "/translate"]]},
    {"key": "struggling", "email": "ishaan@sunrise.school", "label": "Hindi learner", "role": "Student",
     "summary": "Class 8. Uses TatvaX in Hindi and is finding things hard: low scores, a full review deck.",
     "start": "/",
     "tour": [["The interface in Hindi", "/"], ["A chat in Hindi", "/learn/science"], ["Mistakes to review", "/review"],
              ["Progress report (PDF)", "/print/report"], ["TatvAI school helper", "/tatvai"]]},
    {"key": "guest", "email": None, "label": "New visitor", "role": "No account",
     "summary": "Someone trying TatvaX for the first time: everything works without signing up.", "start": "/",
     "tour": [["The home page", "/"], ["Ask a question", "/learn/all"], ["Take an assessment", "/assessments"],
              ["Read the study notes", "/notes"]]},
]

bp = Blueprint("demo", __name__, url_prefix="/api/demo")


def _demo_only():
    """The demo endpoints exist only when TatvaX was started with --demo."""
    from .security import error

    if not current_app.config.get("DEMO_MODE"):
        return error("Not found", 404)
    return None


def _initials(name: str) -> str:
    parts = [p for p in name.replace("Dr. ", "").split() if p]
    return "".join(p[0] for p in parts[:2]).upper()


@bp.get("")
def personas():
    if (blocked := _demo_only()) is not None:
        return blocked
    from .db import get_db
    from .users import current_user

    conn, user = get_db(), current_user()
    current = user["email"] if user is not None and not user["is_guest"] else None
    out = []
    for persona in PERSONAS:
        row = conn.execute("SELECT name FROM users WHERE email = ?", (persona["email"],)).fetchone() if persona["email"] else None
        if persona["email"] and row is None:
            continue  # an older demo school without this account
        name = row["name"] if row else "Visitor"
        out.append({k: v for k, v in persona.items() if k != "email"}
                   | {"name": name, "initials": _initials(name) if row else "?", "active": persona["email"] == current})
    return {"school": SCHOOL, "personas": out}


@bp.post("/switch")
def switch():
    """Sign in as one of the demo accounts, no password needed (demo mode only)."""
    if (blocked := _demo_only()) is not None:
        return blocked
    from .db import get_db
    from .security import error
    from .users import _login

    key = (request.get_json(silent=True) or {}).get("persona")
    persona = next((p for p in PERSONAS if p["key"] == key), None)
    if persona is None:
        return error("Unknown demo account")
    if persona["email"] is None:
        session.clear()  # a brand-new visitor: the next request makes a fresh guest profile
        return {"ok": True, "start": persona["start"]}
    row = get_db().execute("SELECT id FROM users WHERE email = ? AND is_guest = 0", (persona["email"],)).fetchone()
    if row is None:
        return error("That demo account doesn't exist. Rebuild the demo with: python run.py --demo-reset", 404)
    _login(row["id"])
    return {"ok": True, "start": persona["start"]}


# --------------------------------------------------------------------------- entry points

def build(instance_dir: Path = DEFAULT_DIR, reset: bool = False, seed: int = 2026) -> Path:
    """Create the demo school in instance_dir. Returns the path of DEMO_ACCOUNTS.txt."""
    instance_dir = Path(instance_dir)
    database = instance_dir / "tatvax.db"
    if database.exists():
        if not reset:
            raise FileExistsError(f"A demo school already exists in {instance_dir}. Use --reset to rebuild it.")
        shutil.rmtree(instance_dir)
    instance_dir.mkdir(parents=True, exist_ok=True)

    from . import create_app
    from .db import connect

    # No AI and no web translation while building, so it's quick, offline and always the same.
    app = create_app({"INSTANCE_DIR": instance_dir, "DATABASE": str(database), "AI_ALLOWED": False, "WEB_TRANSLATION": False})
    conn = connect(str(database))
    try:
        school = _School(app, conn, random.Random(seed))
        with app.app_context():
            school.make_roles()
            school.make_people()
            school.learning_history()
            school.review_deck()
            school.assignments()
            school.todos()
            school.reading_and_feedback()
            school.finish()
        conn.commit()
    finally:
        conn.close()
    return write_accounts(instance_dir)


def write_accounts(instance_dir: Path) -> Path:
    lines = [f"{SCHOOL}: TatvaX demo accounts", "",
             "Start with:  python run.py --demo",
             "No passwords needed: the demo bar at the top of every page switches between these accounts in one click,",
             "and “What to show” lists the features to present for each:", ""]
    for persona in PERSONAS:
        lines.append(f"  {persona['label']:<15} {persona['role']:<24} {persona['summary']}")
    lines += ["", "Everyone below can also sign in normally (handy on another device).",
              f"Every account's password: {DEMO_PASSWORD}", "", "STAFF (highest role first)"]
    for name, email, _roles, title in STAFF:
        lines.append(f"  {email:<34} {name}  ({title})")
    lines += ["", "STUDENTS"]
    for name, email, grade, language, kind, extra in STUDENTS:
        note = {"star": "top of the leaderboard, long streak", "steady": "regular learner",
                "struggling": "needs support, low scores", "new": "joined this week"}[kind]
        role = f", {extra[0]}" if extra else ""
        lines.append(f"  {email:<34} {name}  (Class {grade}, {language}, {note}{role})")
    lines += ["", "The school has no AI key, so answers come from the study notes. Add a free key in",
              "Teacher console > AI settings (signed in as the principal) to show the AI tutor."]
    path = instance_dir / "DEMO_ACCOUNTS.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=f"Build the TatvaX demo school ({SCHOOL}).")
    parser.add_argument("--dir", default=str(DEFAULT_DIR), help="folder for the demo (default: instance-demo/)")
    parser.add_argument("--reset", action="store_true", help="delete and rebuild an existing demo school")
    args = parser.parse_args(argv)
    try:
        accounts = build(Path(args.dir), reset=args.reset)
    except FileExistsError as exc:
        raise SystemExit(str(exc)) from None
    print(accounts.read_text(encoding="utf-8"))
    print(f"Saved to {accounts}\nStart it with:  python run.py --demo")


if __name__ == "__main__":
    main()
