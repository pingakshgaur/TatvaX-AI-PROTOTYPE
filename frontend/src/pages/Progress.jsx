import {
  Award, Brain, ClipboardCheck, Flame, GraduationCap, Languages, Search, Sprout, TrendingUp, Trophy, Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { BarList, ColumnChart, Ring } from "../components/Charts.jsx";
import { useCrumbs, useShell } from "../components/Shell.jsx";
import { EmptyState, Loading, PageHeader, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { formatNumber, shortDate, timeAgo } from "../lib/format.js";

// Badge icon names sent by the API (see tatvax/gamification.py).
const BADGE_ICONS = {
  sprout: Sprout, search: Search, "graduation-cap": GraduationCap, "clipboard-check": ClipboardCheck,
  trophy: Trophy, brain: Brain, flame: Flame, zap: Zap, languages: Languages, award: Award,
};

function BadgeIcon({ name }) {
  const Icon = BADGE_ICONS[name] || Award;
  return <Icon size={18} strokeWidth={1.75} aria-hidden="true" />;
}

export default function Progress() {
  const { t, user } = useApp();
  const { openAccount } = useShell();
  const [data, setData] = useState(null);
  useCrumbs([{ label: t("nav_progress") }]);

  useEffect(() => {
    let live = true;
    Promise.all([api("/api/progress"), api("/api/leaderboard").catch(() => ({ leaderboard: [], me: null }))])
      .then(([p, l]) => live && setData({ progress: p.progress, leaderboard: l.leaderboard, me: l.me }))
      .catch(() => live && setData({ progress: null, leaderboard: [], me: null }));
    return () => { live = false; };
  }, [user?.id, user?.xp]);

  if (!data) return <Loading />;
  const { progress, leaderboard, me } = data;

  if (!progress) {
    return (
      <>
        <PageHeader eyebrow={t("group_account")} title={t("progress_title")} />
        <Panel>
          <EmptyState icon={TrendingUp} title="No activity yet"
            action={<Link className="btn" to="/subjects">{t("card_learn")}</Link>}>
            Ask a question or complete an assessment to start earning XP, streaks and achievements.
          </EmptyState>
        </Panel>
      </>
    );
  }

  const earned = progress.badges.filter((b) => b.earned).length;

  return (
    <>
      <PageHeader eyebrow={t("group_account")} title={t("progress_title")}
        actions={user?.is_guest && <button className="btn" type="button" onClick={() => openAccount("register")}>{t("create_account")}</button>} />
      {user?.is_guest && (
        <div className="panel" style={{ marginBottom: 20, background: "var(--accent-tint)", borderColor: "transparent" }}>
          <div className="panel-body small">{t("guest_note")}</div>
        </div>
      )}

      <div className="kpi-strip">
        <div className="kpi" style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <Ring fraction={progress.progress} size={78} stroke={7} label={String(progress.level)} sub={t("level")} />
          <div>
            <span className="eyebrow">{t("xp")}</span>
            <span className="value">{formatNumber(progress.xp)}</span>
            <span className="meta">{t("xp_to_next", { n: formatNumber(progress.next_level_xp - progress.xp), level: progress.level + 1 })}</span>
          </div>
        </div>
        <div className="kpi">
          <span className="eyebrow">{t("day_streak")}</span>
          <span className="value">{progress.streak.current}</span>
          <span className="meta">{t("best_streak", { n: progress.streak.best })}</span>
        </div>
        <div className="kpi">
          <span className="eyebrow">{t("questions_asked")}</span>
          <span className="value">{formatNumber(progress.questions_total)}</span>
        </div>
        <div className="kpi">
          <span className="eyebrow">{t("badges")}</span>
          <span className="value">{earned}<small> / {progress.badges.length}</small></span>
        </div>
      </div>

      <div className="grid grid-2 section">
        <Panel title={t("activity")}>
          <p className="hint" style={{ marginTop: -4 }}>Questions asked and assessments completed per day</p>
          <ColumnChart caption={t("activity")} valueName="Activity" items={progress.activity.map((d) => ({
            label: shortDate(d.day), value: d.questions + d.quizzes,
            display: `${d.questions} questions, ${d.quizzes} assessments`,
          }))} />
        </Panel>
        <Panel title={t("by_subject")}>
          {progress.subjects.length
            ? <BarList caption={t("by_subject")} valueName={t("questions")}
                items={progress.subjects.map((s) => ({ label: s.subject || t("all_subjects"), value: s.questions }))} />
            : <p className="muted">No questions yet.</p>}
        </Panel>
      </div>

      <section className="section">
        <div className="section-head"><h2>{t("badges")}</h2><span className="eyebrow">{earned} of {progress.badges.length} unlocked</span></div>
        <div className="badge-grid">
          {progress.badges.map((b) => (
            <div key={b.id} className={`badge-cell${b.earned ? "" : " locked"}`}>
              <span className="badge-mark"><BadgeIcon name={b.icon} /></span>
              <div>
                <strong>{b.name}</strong>
                <span>{b.description}</span>
                <span className="sr-only">{b.earned ? "Unlocked" : "Locked"}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="grid grid-2 section">
        <Panel title={t("recent_quizzes")} tight>
          {progress.quizzes.length ? (
            <table className="table">
              <thead><tr><th>Subject</th><th>Topic</th><th className="num">Score</th><th>Completed</th></tr></thead>
              <tbody>{progress.quizzes.map((q) => (
                <tr key={q.id}>
                  <td>{q.subject}</td>
                  <td className="muted">{q.topic || "General"}</td>
                  <td className="num"><span className={`tag ${q.score / q.total >= 0.6 ? "positive" : "negative"}`}>{q.score}/{q.total}</span></td>
                  <td className="muted small">{timeAgo(q.completed_at)}</td>
                </tr>
              ))}</tbody>
            </table>
          ) : <div className="panel-body muted">No assessments yet. <Link to="/assessments">{t("start_quiz")}</Link></div>}
        </Panel>
        <Panel title={t("leaderboard")} tight>
          {leaderboard.length ? (
            <table className="table">
              <thead><tr><th className="num">#</th><th>Learner</th><th className="num">{t("level")}</th><th className="num">XP this week</th></tr></thead>
              <tbody>{leaderboard.map((row) => (
                <tr key={row.id} className={row.id === me ? "highlight" : ""}>
                  <td className="num mono">{row.rank}</td>
                  <td>{row.name}{row.id === me && <span className="tag primary" style={{ marginLeft: 8 }}>{t("you")}</span>}</td>
                  <td className="num">{row.level}</td>
                  <td className="num">{formatNumber(row.weekly_xp)}</td>
                </tr>
              ))}</tbody>
            </table>
          ) : <div className="panel-body muted">{t("leaderboard_empty")}</div>}
        </Panel>
      </div>
    </>
  );
}
