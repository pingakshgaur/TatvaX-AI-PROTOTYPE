"""XP, levels, daily streaks, daily goals and achievements."""

import json
import math
from datetime import date, timedelta

from .db import now_iso, today

QUESTION_XP = 5
QUESTION_XP_DAILY_CAP = 100
DAILY_BONUS_XP = 10
DAILY_GOAL_XP = 15
QUIZ_COMPLETION_XP = 10
QUIZ_CORRECT_XP = 5
QUIZ_PERFECT_BONUS_XP = 20
TIMED_BONUS_XP = 10
# Assessment XP (completion, correct answers and bonuses) is capped per day, so retaking the same
# assessment over and over can't climb the leaderboard.
QUIZ_XP_DAILY_CAP = 250
QUIZ_XP_REASONS = ("quiz", "perfect_quiz", "timed_bonus")
TIME_GRACE_S = 30  # matches quiz.TIME_GRACE_S

DEFAULT_DAILY_GOAL = 5

# badge id: (Lucide icon name, title, description, rarity)
BADGES = {
    "first_question": ("sprout", "First Step", "Ask your first question", "common"),
    "first_quiz": ("clipboard-check", "Quiz Starter", "Finish your first assessment", "common"),
    "curious_25": ("search", "Curious Mind", "Ask 25 questions", "rare"),
    "streak_3": ("flame", "On Fire", "Learn 3 days in a row", "rare"),
    "polyglot": ("languages", "Polyglot", "Learn in 3 different languages", "rare"),
    "all_rounder": ("award", "All-Rounder", "Ask questions in 4 different subjects", "rare"),
    "explorer": ("compass", "Explorer", "Take assessments in 3 different subjects", "rare"),
    "perfect_quiz": ("trophy", "Perfectionist", "Score 100% on an assessment of 5+ questions", "epic"),
    "marathon": ("timer", "Marathon Mind", "Finish an assessment of 20 or more questions", "epic"),
    "speedster": ("zap", "Speedster", "Score 80% or more in a timed assessment", "epic"),
    "quiz_master": ("brain", "Quiz Master", "Finish 10 assessments", "epic"),
    "streak_7": ("crown", "Unstoppable", "Learn 7 days in a row", "legendary"),
    "scholar_100": ("graduation-cap", "Scholar", "Ask 100 questions", "legendary"),
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


def _xp(conn, user_id: int) -> int:
    row = conn.execute("SELECT xp FROM users WHERE id = ?", (user_id,)).fetchone()
    return row["xp"] if row else 0


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


def daily_goal_status(conn, user_id: int) -> dict:
    user = conn.execute("SELECT daily_goal FROM users WHERE id = ?", (user_id,)).fetchone()
    goal = (user["daily_goal"] if user and user["daily_goal"] else DEFAULT_DAILY_GOAL)
    row = conn.execute("SELECT questions, quizzes FROM activity WHERE user_id = ? AND day = ?", (user_id, today())).fetchone()
    done = (row["questions"] + row["quizzes"]) if row else 0
    return {"done": done, "goal": goal, "complete": done >= goal}


def _goal_reached_now(conn, user_id: int) -> tuple[bool, int]:
    """Award the daily-goal bonus the first time today's goal is met. Returns (reached_now, xp)."""
    status = daily_goal_status(conn, user_id)
    if not status["complete"]:
        return False, 0
    already = conn.execute(
        "SELECT 1 FROM xp_events WHERE user_id = ? AND reason = 'daily_goal' AND created_at >= ?", (user_id, today())
    ).fetchone()
    if already:
        return False, 0
    return True, award_xp(conn, user_id, "daily_goal", DAILY_GOAL_XP)


def _reward(conn, user_id: int, xp_before: int, gained: int) -> dict:
    goal_now, goal_xp = _goal_reached_now(conn, user_id)
    after = _xp(conn, user_id)
    level_before, level_after = level_info(xp_before)["level"], level_info(after)["level"]
    return {
        "xp": gained + goal_xp,
        "badges": check_badges(conn, user_id),
        "level_up": level_after if level_after > level_before else None,
        "goal": {**daily_goal_status(conn, user_id), "reached_now": goal_now, "bonus_xp": goal_xp},
    }


def record_question(conn, user_id: int, mode: str, subject: str | None, language: str) -> dict:
    """Log a question and award XP. Returns {'xp', 'badges', 'level_up', 'goal'}."""
    xp_before = _xp(conn, user_id)
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
    return _reward(conn, user_id, xp_before, gained)


def record_quiz(conn, user_id: int, score: int, total: int, mode: str = "practice", on_time: bool = True) -> dict:
    xp_before = _xp(conn, user_id)
    first_today = _touch_day(conn, user_id, quizzes=1)
    gained = award_xp(conn, user_id, "daily_bonus", DAILY_BONUS_XP) if first_today else 0
    marks = ", ".join("?" for _ in QUIZ_XP_REASONS)
    earned_today = conn.execute(
        f"SELECT COALESCE(SUM(points), 0) FROM xp_events WHERE user_id = ? AND reason IN ({marks}) AND created_at >= ?",
        (user_id, *QUIZ_XP_REASONS, today()),
    ).fetchone()[0]
    room = max(0, QUIZ_XP_DAILY_CAP - earned_today)
    for reason, points, earned in (
        ("quiz", QUIZ_COMPLETION_XP + QUIZ_CORRECT_XP * score, True),
        ("perfect_quiz", QUIZ_PERFECT_BONUS_XP, total >= 5 and score == total),
        ("timed_bonus", TIMED_BONUS_XP, mode == "timed" and on_time and total and score / total >= 0.8),
    ):
        if earned and room:
            points = min(points, room)
            room -= points
            gained += award_xp(conn, user_id, reason, points)
    return _reward(conn, user_id, xp_before, gained)


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


def _quiz_subjects(row) -> list[str]:
    if row["subjects_json"]:
        try:
            return json.loads(row["subjects_json"])
        except json.JSONDecodeError:
            pass
    return [row["subject"]]


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
    quizzes = conn.execute(
        "SELECT subject, subjects_json, score, total, mode, time_limit, duration_s FROM quizzes WHERE user_id = ? AND completed_at IS NOT NULL",
        (user_id,),
    ).fetchall()
    quiz_subjects = {s for q in quizzes for s in _quiz_subjects(q)}
    streak = streaks(conn, user_id)["current"]

    earned_now = {
        "first_question": stats["questions"] >= 1,
        "curious_25": stats["questions"] >= 25,
        "scholar_100": stats["questions"] >= 100,
        "first_quiz": len(quizzes) >= 1,
        "perfect_quiz": any(q["total"] >= 5 and q["score"] == q["total"] for q in quizzes),
        "quiz_master": len(quizzes) >= 10,
        "marathon": any(q["total"] >= 20 for q in quizzes),
        "speedster": any(q["mode"] == "timed" and q["total"] and q["score"] / q["total"] >= 0.8
                         and (q["duration_s"] is None or q["time_limit"] is None or q["duration_s"] <= q["time_limit"] + TIME_GRACE_S)
                         for q in quizzes),
        "explorer": len(quiz_subjects) >= 3,
        "streak_3": streak >= 3,
        "streak_7": streak >= 7,
        "polyglot": stats["languages"] >= 3,
        "all_rounder": stats["subjects"] >= 4,
    }
    new = []
    for badge, earned in earned_now.items():
        if earned and badge not in have:
            conn.execute("INSERT INTO badges (user_id, badge, earned_at) VALUES (?, ?, ?)", (user_id, badge, now_iso()))
            new.append(badge_dict(badge, earned=True, earned_at=now_iso()))
    return new


def badge_dict(badge: str, earned: bool, earned_at: str | None = None) -> dict:
    icon, name, description, rarity = BADGES[badge]
    return {"id": badge, "icon": icon, "name": name, "description": description, "rarity": rarity,
            "earned": earned, "earned_at": earned_at}


def progress(conn, user_id: int) -> dict:
    user = conn.execute("SELECT xp, is_guest, leaderboard FROM users WHERE id = ?", (user_id,)).fetchone()
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
    titles = {r["slug"]: r["title"] for r in conn.execute("SELECT slug, title FROM documents")}
    quizzes = []
    for r in conn.execute(
        """SELECT id, subject, subjects_json, topic, score, total, mode, completed_at FROM quizzes
           WHERE user_id = ? AND completed_at IS NOT NULL ORDER BY completed_at DESC LIMIT 10""",
        (user_id,),
    ):
        names = [titles.get(s, s) for s in _quiz_subjects(r)]
        quizzes.append({"id": r["id"], "subject": ", ".join(names), "topic": r["topic"], "score": r["score"],
                        "total": r["total"], "mode": r["mode"], "completed_at": r["completed_at"]})

    totals = conn.execute("SELECT COUNT(*) FROM question_log WHERE user_id = ?", (user_id,)).fetchone()[0]
    rank = None
    if user and not user["is_guest"] and user["leaderboard"]:
        rank = next((row["rank"] for row in leaderboard(conn, limit=1000) if row["id"] == user_id), None)
    order = ["legendary", "epic", "rare", "common"]
    badges = sorted((badge_dict(b, b in earned, earned.get(b)) for b in BADGES),
                    key=lambda b: (not b["earned"], order.index(b["rarity"]) if b["earned"] else -order.index(b["rarity"])))
    return {
        **level_info(user["xp"] if user else 0),
        "streak": streaks(conn, user_id),
        "goal": daily_goal_status(conn, user_id),
        "rank": rank,
        "questions_total": totals,
        "badges": badges,
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
           WHERE x.created_at >= ? AND u.is_guest = 0 AND u.leaderboard = 1 AND u.role = 'student'
           GROUP BY u.id ORDER BY weekly_xp DESC, u.xp DESC LIMIT ?""",
        (since, limit),
    ).fetchall()
    return [
        {"rank": i + 1, "id": r["id"], "name": r["name"], "weekly_xp": r["weekly_xp"], "level": level_info(r["xp"])["level"]}
        for i, r in enumerate(rows)
    ]
