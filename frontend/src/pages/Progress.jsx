import { Target, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { BarList, ColumnChart, Ring } from "../components/Charts.jsx";
import { useCrumbs, useShell } from "../components/Shell.jsx";
import { CountUp, EmptyState, Loading, PageHeader, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { BadgeIcon, RARITY_COLOR } from "../lib/badgeIcons.jsx";
import { formatNumber, shortDate, timeAgo } from "../lib/format.js";

export default function Progress() {
  const { t, user, progressVersion } = useApp();
  const { openAccount } = useShell();
  const location = useLocation();
  const [data, setData] = useState(null);
  useCrumbs([{ label: t("nav_progress") }]);

  useEffect(() => {
    let live = true;
    Promise.all([api("/api/progress"), api("/api/leaderboard").catch(() => ({ leaderboard: [], me: null }))])
      .then(([p, l]) => live && setData({ progress: p.progress, leaderboard: l.leaderboard, me: l.me }))
      .catch(() => live && setData({ progress: null, leaderboard: [], me: null }));
    return () => { live = false; };
  }, [user?.id, progressVersion]);

  // Links like /progress#achievements jump to that section once the data has loaded.
  useEffect(() => {
    if (!data || !location.hash) return;
    const el = document.getElementById(location.hash.slice(1));
    if (el) requestAnimationFrame(() => { el.scrollIntoView({ behavior: "smooth", block: "start" }); el.classList.add("flash"); });
  }, [data, location.hash]);

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
            <span className="value"><CountUp value={progress.xp} /></span>
            <span className="meta">{t("xp_to_next", { n: formatNumber(progress.next_level_xp - progress.xp), level: progress.level + 1 })}</span>
          </div>
        </div>
        <div className="kpi">
          <span className="eyebrow">{t("day_streak")}</span>
          <span className="value"><CountUp value={progress.streak.current} /></span>
          <span className="meta">{t("best_streak", { n: progress.streak.best })}</span>
        </div>
        <div className="kpi">
          <span className="eyebrow"><Target size={12} style={{ verticalAlign: "-2px" }} /> Daily goal</span>
          <span className="value"><CountUp value={Math.min(progress.goal.done, progress.goal.goal)} /><small> / {progress.goal.goal}</small></span>
          <div className="goal-bar"><span style={{ width: `${Math.min(100, (progress.goal.done / progress.goal.goal) * 100)}%` }} /></div>
          <span className="meta">{progress.goal.complete ? "Complete for today" : "Change it from your profile menu"}</span>
        </div>
        <div className="kpi">
          <span className="eyebrow">{t("questions_asked")}</span>
          <span className="value"><CountUp value={progress.questions_total} /></span>
          <span className="meta">{progress.rank ? `Rank #${progress.rank} this week` : "Join the weekly leaderboard by creating an account"}</span>
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

      <section className="section" id="achievements" style={{ scrollMarginTop: 80, borderRadius: 12 }}>
        <div className="section-head"><h2>{t("badges")}</h2><span className="eyebrow">{earned} of {progress.badges.length} unlocked</span></div>
        <div className="badge-grid rich stagger">
          {progress.badges.map((b, i) => (
            <div key={b.id} className={`badge-cell lift${b.earned ? "" : " locked"}`} style={{ "--rarity": RARITY_COLOR[b.rarity], "--i": i }}>
              <span className="badge-mark"><BadgeIcon name={b.icon} size={20} /></span>
              <div>
                <strong>{b.name}</strong>
                <span>{b.description}</span>
                <span className="rarity">{b.rarity}{b.earned && b.earned_at ? ` · ${timeAgo(b.earned_at)}` : ""}</span>
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
        <Panel title={<h2 id="leaderboard" style={{ scrollMarginTop: 80 }}>{t("leaderboard")}</h2>} tight>
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
