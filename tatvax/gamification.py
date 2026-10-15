"""XP, levels, daily streaks and badges."""

import math
from datetime import date, timedelta

from .db import now_iso, today

QUESTION_XP = 5
QUESTION_XP_DAILY_CAP = 100
DAILY_BONUS_XP = 10
QUIZ_COMPLETION_XP = 10
QUIZ_CORRECT_XP = 5
QUIZ_PERFECT_BONUS_XP = 20

# badge id: (Lucide icon name, title, description)
BADGES = {
    "first_question": ("sprout", "First Step", "Ask your first question"),
    "curious_25": ("search", "Curious Mind", "Ask 25 questions"),
    "scholar_100": ("graduation-cap", "Scholar", "Ask 100 questions"),
    "first_quiz": ("clipboard-check", "Quiz Starter", "Finish your first quiz"),
    "perfect_quiz": ("trophy", "Perfectionist", "Score 100% on a quiz of 5+ questions"),
    "quiz_master": ("brain", "Quiz Master", "Finish 10 quizzes"),
    "streak_3": ("flame", "On Fire", "Learn 3 days in a row"),
    "streak_7": ("zap", "Unstoppable", "Learn 7 days in a row"),
    "polyglot": ("languages", "Polyglot", "Learn in 3 different languages"),
    "all_rounder": ("award", "All-Rounder", "Ask questions in 4 different subjects"),
}


def xp_for_level(level: int) -> int:
    """Total XP needed to reach a level: 0, 100, 300, 600, 1000, ..."""
    return 50 * level * (level - 1)


def level_info(xp: int) -> dict:
    level = int((1 + math.sqrt(1 + 8 * max(xp, 0) / 100)) / 2)
    floor, ceiling = xp_for_level(level), xp_for_level(level + 1)
    return {
        "level": level,
        "xp": xp,
        "level_floor": floor,
        "next_level_xp": ceiling,
        "progress": round((xp - floor) / (ceiling - floor), 3),
    }


def award_xp(conn, user_id: int, reason: str, points: int) -> int:
    if points <= 0:
        return 0
    conn.execute(
        "INSERT INTO xp_events (user_id, reason, points, created_at) VALUES (?, ?, ?, ?)",
        (user_id, reason, points, now_iso()),
    )
    conn.execute("UPDATE users SET xp = xp + ? WHERE id = ?", (points, user_id))
    return points


def _touch_day(conn, user_id: int, questions: int = 0, quizzes: int = 0) -> bool:
    """Record activity for today. Returns True if this is the first activity of the day."""
    day = today()
    first = conn.execute("SELECT 1 FROM activity WHERE user_id = ? AND day = ?", (user_id, day)).fetchone() is None
    conn.execute(
        """INSERT INTO activity (user_id, day, questions, quizzes) VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, day) DO UPDATE SET questions = questions + excluded.questions,
                                                   quizzes = quizzes + excluded.quizzes""",
        (user_id, day, questions, quizzes),
    )
    return first


def record_question(conn, user_id: int, mode: str, subject: str | None, language: str) -> dict:
    """Log a question and award XP. Returns {'xp': gained, 'badges': [new badges]}."""
    conn.execute(
        "INSERT INTO question_log (user_id, mode, subject, language, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, mode, subject, language, now_iso()),
    )
    first_today = _touch_day(conn, user_id, questions=1)
    gained = award_xp(conn, user_id, "daily_bonus", DAILY_BONUS_XP) if first_today else 0
    earned_today = conn.execute(
        "SELECT COALESCE(SUM(points), 0) FROM xp_events WHERE user_id = ? AND reason = 'question' AND created_at >= ?",
        (user_id, today()),
    ).fetchone()[0]
    if earned_today < QUESTION_XP_DAILY_CAP:
        gained += award_xp(conn, user_id, "question", QUESTION_XP)
    return {"xp": gained, "badges": check_badges(conn, user_id)}


def record_quiz(conn, user_id: int, score: int, total: int) -> dict:
    first_today = _touch_day(conn, user_id, quizzes=1)
    gained = award_xp(conn, user_id, "daily_bonus", DAILY_BONUS_XP) if first_today else 0
    gained += award_xp(conn, user_id, "quiz", QUIZ_COMPLETION_XP + QUIZ_CORRECT_XP * score)
    if total >= 5 and score == total:
        gained += award_xp(conn, user_id, "perfect_quiz", QUIZ_PERFECT_BONUS_XP)
    return {"xp": gained, "badges": check_badges(conn, user_id)}


def streaks(conn, user_id: int) -> dict:
    days = [date.fromisoformat(r["day"]) for r in conn.execute(
        "SELECT day FROM activity WHERE user_id = ? ORDER BY day DESC", (user_id,)
    )]
    if not days:
        return {"current": 0, "best": 0}
    current = 0
    expected = date.fromisoformat(today())
    if days[0] == expected - timedelta(days=1):
        expected = days[0]  # streak is still alive if the student learned yesterday
    for day in days:
        if day == expected:
            current += 1
            expected -= timedelta(days=1)
        elif day < expected:
            break
    best, run = 1, 1
    for newer, older in zip(days, days[1:]):
        run = run + 1 if newer - older == timedelta(days=1) else 1
        best = max(best, run)
    return {"current": current, "best": max(best, current)}


def check_badges(conn, user_id: int) -> list[dict]:
    """Award any newly earned badges and return them."""
    have = {r["badge"] for r in conn.execute("SELECT badge FROM badges WHERE user_id = ?", (user_id,))}
    stats = conn.execute(
        """SELECT COUNT(*) AS questions,
                  COUNT(DISTINCT language) AS languages,
                  COUNT(DISTINCT CASE WHEN mode = 'subject' THEN subject END) AS subjects
           FROM question_log WHERE user_id = ?""",
        (user_id,),
    ).fetchone()
    quiz = conn.execute(
        """SELECT COUNT(*) AS done,
                  SUM(CASE WHEN score = total AND total >= 5 THEN 1 ELSE 0 END) AS perfect
           FROM quizzes WHERE user_id = ? AND completed_at IS NOT NULL""",
        (user_id,),
    ).fetchone()
    streak = streaks(conn, user_id)["current"]

    earned_now = {
        "first_question": stats["questions"] >= 1,
        "curious_25": stats["questions"] >= 25,
        "scholar_100": stats["questions"] >= 100,
        "first_quiz": quiz["done"] >= 1,
        "perfect_quiz": (quiz["perfect"] or 0) >= 1,
        "quiz_master": quiz["done"] >= 10,
        "streak_3": streak >= 3,
        "streak_7": streak >= 7,
        "polyglot": stats["languages"] >= 3,
        "all_rounder": stats["subjects"] >= 4,
    }
    new = []
    for badge, earned in earned_now.items():
        if earned and badge not in have:
            conn.execute("INSERT INTO badges (user_id, badge, earned_at) VALUES (?, ?, ?)", (user_id, badge, now_iso()))
            new.append(badge_dict(badge, earned=True))
    return new


def badge_dict(badge: str, earned: bool, earned_at: str | None = None) -> dict:
    icon, name, description = BADGES[badge]
    return {"id": badge, "icon": icon, "name": name, "description": description, "earned": earned, "earned_at": earned_at}


def progress(conn, user_id: int) -> dict:
    user = conn.execute("SELECT xp FROM users WHERE id = ?", (user_id,)).fetchone()
    earned = {r["badge"]: r["earned_at"] for r in conn.execute(
        "SELECT badge, earned_at FROM badges WHERE user_id = ?", (user_id,)
    )}
    start = (date.fromisoformat(today()) - timedelta(days=13)).isoformat()
    activity = {r["day"]: r for r in conn.execute(
        "SELECT day, questions, quizzes FROM activity WHERE user_id = ? AND day >= ?", (user_id, start)
    )}
    days = []
    for offset in range(13, -1, -1):
        day = (date.fromisoformat(today()) - timedelta(days=offset)).isoformat()
        row = activity.get(day)
        days.append({"day": day, "questions": row["questions"] if row else 0, "quizzes": row["quizzes"] if row else 0})

    subjects = [dict(r) for r in conn.execute(
        """SELECT COALESCE(d.title, q.subject) AS subject, COUNT(*) AS questions
           FROM question_log q LEFT JOIN documents d ON d.slug = q.subject
           WHERE q.user_id = ? GROUP BY q.subject ORDER BY questions DESC""",
        (user_id,),
    )]
    quizzes = [dict(r) for r in conn.execute(
        """SELECT q.id, COALESCE(d.title, q.subject) AS subject, q.topic, q.score, q.total, q.completed_at
           FROM quizzes q LEFT JOIN documents d ON d.slug = q.subject
           WHERE q.user_id = ? AND q.completed_at IS NOT NULL ORDER BY q.completed_at DESC LIMIT 10""",
        (user_id,),
    )]
    totals = conn.execute(
        "SELECT COUNT(*) FROM question_log WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    return {
        **level_info(user["xp"] if user else 0),
        "streak": streaks(conn, user_id),
        "questions_total": totals,
        "badges": [badge_dict(b, b in earned, earned.get(b)) for b in BADGES],
        "activity": days,
        "subjects": subjects,
        "quizzes": quizzes,
    }


def leaderboard(conn, limit: int = 10) -> list[dict]:
    """Top learners by XP earned in the last 7 days (registered students who opted in)."""
    since = (date.fromisoformat(today()) - timedelta(days=6)).isoformat()
    rows = conn.execute(
        """SELECT u.id, u.name, SUM(x.points) AS weekly_xp, u.xp
           FROM xp_events x JOIN users u ON u.id = x.user_id
           WHERE x.created_at >= ? AND u.is_guest = 0 AND u.leaderboard = 1
           GROUP BY u.id ORDER BY weekly_xp DESC, u.xp DESC LIMIT ?""",
        (since, limit),
    ).fetchall()
    return [
        {"rank": i + 1, "id": r["id"], "name": r["name"], "weekly_xp": r["weekly_xp"], "level": level_info(r["xp"])["level"]}
        for i, r in enumerate(rows)
    ]
