import {
  ArrowLeft, ArrowRight, Check, CheckCheck, Clock, FileDown, Flag, Flame, History, Layers, Lightbulb, MessageSquareText,
  Play, RotateCcw, Shuffle, Timer, X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { Ring } from "../components/Charts.jsx";
import { useCrumbs } from "../components/Shell.jsx";
import SubjectArt from "../components/SubjectArt.jsx";
import { Dialog, InlineMarkdown, Markdown, Meter, PageHeader, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";

const KEYS = ["A", "B", "C", "D"];
const PRESETS = [5, 10, 15, 20, 30];
const SECONDS = { easy: 45, medium: 60, hard: 90, mixed: 60 };
const MODES = [
  ["practice", Lightbulb, "Practice", "See the answer and an explanation after every question.", "var(--c-teal)"],
  ["exam", Layers, "Exam", "Answer everything first, then get your score and review.", "var(--c-indigo)"],
  ["timed", Timer, "Timed", "Exam mode against the clock. Score 80% or more for bonus XP.", "var(--c-coral)"],
];

export const formatTime = (seconds) => `${Math.floor(seconds / 60)}:${String(Math.max(0, seconds) % 60).padStart(2, "0")}`;

// ------------------------------------------------------------------ builder

function Builder({ initialSubjects, initialTopic, onStart }) {
  const { t, app, lang } = useApp();
  const [subjects, setSubjects] = useState(initialSubjects);
  const [topic, setTopic] = useState(initialTopic);
  const [count, setCount] = useState(10);
  const [difficulty, setDifficulty] = useState("medium");
  const [mode, setMode] = useState("practice");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const toggle = (slug) => setSubjects((list) => (list.includes(slug) ? list.filter((s) => s !== slug) : [...list, slug]));
  const allSelected = subjects.length === app.subjects.length;
  const chosen = app.subjects.filter((s) => subjects.includes(s.slug));
  const minutes = Math.max(1, Math.round((count * SECONDS[difficulty]) / 60));

  const start = async () => {
    setBusy(true);
    setError("");
    try {
      const { quiz } = await api("/api/quiz", { method: "POST", body: { subjects, topic, count, difficulty, mode, language: lang } });
      onStart(quiz);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader eyebrow={t("group_practice")} title={t("quiz_title")} lede={t("quiz_sub")}
        actions={<Link className="btn btn-secondary" to="/assessments/history"><History size={15} /> {t("my_assessments")}</Link>} />
      <div className="builder">
        <div>
          <section className="builder-step">
            <div className="label"><span className="step-num">1</span> Pick your subjects
              <button className="btn btn-ghost btn-sm" type="button" style={{ marginLeft: "auto" }}
                onClick={() => setSubjects(allSelected ? [] : app.subjects.map((s) => s.slug))}>
                <CheckCheck size={14} /> {allSelected ? "Clear all" : "Select all"}
              </button>
            </div>
            <div className="subject-pick stagger" role="group" aria-label="Subjects">
              {app.subjects.map((s, i) => (
                <button key={s.slug} type="button" aria-pressed={subjects.includes(s.slug)} onClick={() => toggle(s.slug)}
                  style={{ "--tone": s.color, "--i": i }}>
                  <SubjectArt subject={s} size={34} />
                  {s.title}
                  <span className="sp-check" aria-hidden="true"><Check size={12} /></span>
                </button>
              ))}
            </div>
          </section>

          <section className="builder-step">
            <label className="label" htmlFor="quiz-topic"><span className="step-num">2</span> Focus on a topic <span className="muted small">(optional)</span></label>
            <input className="input" id="quiz-topic" dir="auto" maxLength={80} value={topic}
              placeholder={t("topic_placeholder")} onChange={(e) => setTopic(e.target.value)} />
          </section>

          <section className="builder-step">
            <label className="label" htmlFor="quiz-count"><span className="step-num">3</span> How many questions?</label>
            <div className="count-control">
              <input id="quiz-count" type="range" min={3} max={30} value={count} onChange={(e) => setCount(Number(e.target.value))} />
              <span className="count-value" aria-live="polite">{count}</span>
            </div>
            <div className="count-presets" role="group" aria-label="Quick choices">
              {PRESETS.map((n) => <button key={n} type="button" aria-pressed={count === n} onClick={() => setCount(n)}>{n} questions</button>)}
            </div>
          </section>

          <section className="builder-step">
            <div className="label"><span className="step-num">4</span> {t("difficulty")}</div>
            <div className="segmented" role="group" aria-label={t("difficulty")}>
              {["easy", "medium", "hard", "mixed"].map((d) => (
                <button key={d} type="button" aria-pressed={difficulty === d} onClick={() => setDifficulty(d)}>
                  {d === "mixed" ? <><Shuffle size={13} /> Mixed</> : t(d)}
                </button>
              ))}
            </div>
          </section>

          <section className="builder-step">
            <div className="label"><span className="step-num">5</span> Choose a mode</div>
            <div className="mode-cards" role="group" aria-label="Mode">
              {MODES.map(([id, Icon, name, desc, tone]) => (
                <button key={id} type="button" aria-pressed={mode === id} onClick={() => setMode(id)} style={{ "--tone": tone }}>
                  <span className="mc-icon"><Icon size={17} /></span>
                  <strong>{name}</strong>
                  <span>{desc}</span>
                </button>
              ))}
            </div>
          </section>
        </div>

        <aside className="summary-card">
          <Panel title="Your assessment">
            <dl>
              <dt>Subjects</dt><dd>{chosen.length ? chosen.map((s) => s.title).join(", ") : "None yet"}</dd>
              <dt>Questions</dt><dd>{count}</dd>
              <dt>Difficulty</dt><dd style={{ textTransform: "capitalize" }}>{difficulty}</dd>
              <dt>Mode</dt><dd style={{ textTransform: "capitalize" }}>{mode}</dd>
              <dt>{mode === "timed" ? "Time limit" : "About"}</dt><dd>{minutes} min</dd>
              {topic.trim() && <><dt>Topic</dt><dd>{topic}</dd></>}
            </dl>
            {error && <p className="form-error" role="alert">{error}</p>}
            <button className="btn btn-lg btn-block" type="button" disabled={busy || !subjects.length} onClick={start}>
              {busy ? <><span className="spinner" aria-hidden="true" /> {t("making_quiz")}</> : <><Play size={16} /> {t("start_quiz")}</>}
            </button>
            {!subjects.length && <p className="hint" style={{ marginTop: 8 }}>Pick at least one subject to begin.</p>}
            {busy && app.ai_enabled && (
              <p className="hint" role="status" style={{ marginTop: 10 }}>
                The AI is writing {count} fresh questions{chosen.length > 1 ? ` across ${chosen.length} subjects` : ""}.
                {count > 10 ? " Questions are written in parallel batches, so this takes around ten to twenty seconds." : " This usually takes a few seconds."}
              </p>
            )}
          </Panel>
        </aside>
      </div>
    </>
  );
}

// ------------------------------------------------------------------ runners

function QuestionCard({ quiz, index, children }) {
  const q = quiz.questions[index];
  const subject = quiz.subjects.find((s) => s.slug === q.subject);
  return (
    <Panel>
      {quiz.subjects.length > 1 && subject && (
        <span className="tag" style={{ marginBottom: 12, borderColor: subject.color, color: subject.color }}>{subject.title}</span>
      )}
      <Markdown className="prose question-text" source={q.question} />
      {children}
    </Panel>
  );
}

export function PracticeRunner({ quiz, onFinish }) {
  const { t } = useApp();
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);
  const [combo, setCombo] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const started = useRef(Date.now());
  const nextRef = useRef(null);
  const total = quiz.questions.length;

  useEffect(() => { if (result) nextRef.current?.focus(); }, [result]);

  const choose = async (choice) => {
    setBusy(true);
    setError("");
    try {
      const res = await api(`/api/quiz/${quiz.id}/answer`, {
        method: "POST", body: { index, choice, duration_s: Math.round((Date.now() - started.current) / 1000) },
      });
      setResult({ ...res, choice });
      setAnswers((list) => [...list, { ...res, choice }]);
      setCombo((c) => (res.correct ? c + 1 : 0));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const next = () => {
    if (index === total - 1) onFinish({ answers, finished: result.finished });
    else { setIndex(index + 1); setResult(null); }
  };

  return (
    <div className="assessment">
      <div className="runner-top">
        <span className="eyebrow">{t("question_of", { n: index + 1, total })}</span>
        <Meter value={(index + (result ? 1 : 0)) / total} label="Progress" />
        {combo >= 2 && <span className="combo" key={combo}><Flame size={14} /> {combo} in a row</span>}
      </div>
      <QuestionCard quiz={quiz} index={index}>
        <div className="answer-list" role="group" aria-label="Answers">
          {quiz.questions[index].options.map((option, i) => {
            let state = "";
            if (result) {
              if (i === result.answer_index) state = "correct";
              else if (i === result.choice) state = "incorrect";
            }
            return (
              <button key={i} type="button" className={`answer ${state}`} disabled={Boolean(result) || busy} onClick={() => choose(i)}>
                <span className="key" aria-hidden="true">{KEYS[i]}</span>
                <InlineMarkdown source={option} />
                {state === "correct" && <Check className="result-icon ok" size={18} aria-label={t("correct")} />}
                {state === "incorrect" && <X className="result-icon bad" size={18} aria-label={t("incorrect")} />}
              </button>
            );
          })}
        </div>
        {error && <p className="form-error" role="alert" style={{ marginTop: 12 }}>{error}</p>}
        {result && (
          <>
            <div className={`explanation${result.correct ? "" : " incorrect"}`} role="status">
              <span className="eyebrow">{result.correct ? t("correct") : t("incorrect")}</span>
              <Markdown source={result.explanation} />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
              <button ref={nextRef} className="btn" type="button" onClick={next}>
                {index === total - 1 ? t("see_results") : t("next")} <ArrowRight size={15} />
              </button>
            </div>
          </>
        )}
      </QuestionCard>
    </div>
  );
}

export function ExamRunner({ quiz, onFinish }) {
  const { t } = useApp();
  const total = quiz.questions.length;
  const [index, setIndex] = useState(0);
  const [choices, setChoices] = useState(() => Array(total).fill(null));
  const [flags, setFlags] = useState(() => new Set());
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [left, setLeft] = useState(quiz.time_limit);
  const started = useRef(Date.now());
  const submitted = useRef(false);
  const answered = choices.filter((c) => c !== null).length;

  const submit = useCallback(async (finalChoices) => {
    if (submitted.current) return;
    submitted.current = true;
    setBusy(true);
    setConfirm(false);
    try {
      const finished = await api(`/api/quiz/${quiz.id}/submit`, {
        method: "POST", body: { answers: finalChoices, duration_s: Math.round((Date.now() - started.current) / 1000) },
      });
      onFinish({ finished, choices: finalChoices });
    } catch (err) {
      submitted.current = false;
      setError(err.message);
      setBusy(false);
    }
  }, [onFinish, quiz.id]);

  // Countdown for timed mode; time running out submits automatically.
  const choicesRef = useRef(choices);
  choicesRef.current = choices;
  useEffect(() => {
    if (!quiz.time_limit) return undefined;
    const timer = setInterval(() => {
      const remaining = quiz.time_limit - Math.floor((Date.now() - started.current) / 1000);
      setLeft(remaining);
      if (remaining <= 0) {
        clearInterval(timer);
        submit(choicesRef.current);
      }
    }, 500);
    return () => clearInterval(timer);
  }, [quiz.time_limit, submit]);

  const pick = (i) => setChoices((list) => list.map((c, j) => (j === index ? (c === i ? null : i) : c)));
  const toggleFlag = () => setFlags((set) => {
    const next = new Set(set);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    return next;
  });

  return (
    <div className="assessment">
      <div className="runner-top">
        <span className="eyebrow">{t("question_of", { n: index + 1, total })}</span>
        <Meter value={answered / total} label={`${answered} of ${total} answered`} />
        {quiz.time_limit != null && (
          <span className={`timer${left <= 30 ? " low" : ""}`} role="timer" aria-label={`${formatTime(left)} left`}>
            <Clock size={14} /> {formatTime(left)}
          </span>
        )}
      </div>
      <QuestionCard quiz={quiz} index={index}>
        <div className="answer-list" role="radiogroup" aria-label="Answers">
          {quiz.questions[index].options.map((option, i) => (
            <button key={i} type="button" role="radio" aria-checked={choices[index] === i}
              className={`answer${choices[index] === i ? " chosen" : ""}`} onClick={() => pick(i)} disabled={busy}>
              <span className="key" aria-hidden="true">{KEYS[i]}</span>
              <InlineMarkdown source={option} />
            </button>
          ))}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 18 }}>
          <button className="btn btn-secondary" type="button" disabled={index === 0} onClick={() => setIndex(index - 1)}><ArrowLeft size={15} /> Previous</button>
          <button className={`btn ${flags.has(index) ? "" : "btn-ghost"}`} type="button" onClick={toggleFlag} aria-pressed={flags.has(index)}
            style={flags.has(index) ? { background: "var(--c-saffron)", borderColor: "var(--c-saffron)", color: "#1b1405" } : undefined}>
            <Flag size={15} /> {flags.has(index) ? "Flagged" : "Flag for review"}
          </button>
          <span style={{ flex: 1 }} />
          {index < total - 1
            ? <button className="btn" type="button" onClick={() => setIndex(index + 1)}>{t("next")} <ArrowRight size={15} /></button>
            : <button className="btn" type="button" disabled={busy} onClick={() => (answered < total ? setConfirm(true) : submit(choices))}>
                <CheckCheck size={15} /> Submit</button>}
        </div>
        <nav className="qnav" aria-label="Questions">
          {quiz.questions.map((_, i) => (
            <button key={i} type="button" onClick={() => setIndex(i)}
              className={`${choices[i] !== null ? "answered" : ""}${i === index ? " current" : ""}${flags.has(i) ? " flagged" : ""}`}
              aria-label={`Question ${i + 1}${choices[i] !== null ? ", answered" : ""}${flags.has(i) ? ", flagged" : ""}`}
              aria-current={i === index ? "step" : undefined}>{i + 1}</button>
          ))}
        </nav>
        {error && <p className="form-error" role="alert" style={{ marginTop: 12 }}>{error}</p>}
      </QuestionCard>

      <Dialog open={confirm} onClose={() => setConfirm(false)} title="Submit your assessment?">
        <p>You've answered {answered} of {total} questions. Unanswered questions count as incorrect.</p>
        <div className="dialog-footer">
          <button className="btn btn-secondary" type="button" onClick={() => setConfirm(false)}>Keep working</button>
          <button className="btn" type="button" onClick={() => submit(choices)}>Submit now</button>
        </div>
      </Dialog>
    </div>
  );
}

// ------------------------------------------------------------------ results

export function Results({ quiz, outcome, onRestart, onRetry, review: reviewing = false }) {
  const { t, celebrate } = useApp();
  const celebrated = useRef(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState("");
  const { finished } = outcome;
  const total = quiz.questions.length;

  const review = useMemo(() => {
    if (finished?.results) return finished.results;
    return outcome.answers.map((a) => ({ choice: a.choice, correct: a.correct, answer_index: a.answer_index, explanation: a.explanation }));
  }, [finished, outcome.answers]);
  const score = finished?.score ?? review.filter((r) => r.correct).length;
  const ratio = total ? score / total : 0;
  const wrong = review.map((r, i) => ({ ...r, i })).filter((r) => !r.correct);
  const heading = ratio === 1 ? t("great_job") : ratio >= 0.6 ? t("good_job") : t("keep_going");

  useEffect(() => {
    if (finished && !reviewing && !celebrated.current) {
      celebrated.current = true;
      celebrate(finished);
    }
  }, [celebrate, finished, reviewing]);

  const retry = async () => {
    setRetrying(true);
    try {
      const res = await api(`/api/quiz/${quiz.id}/retry`, { method: "POST", body: {} });
      onRetry(res.quiz);
    } catch (err) {
      setError(err.message);
      setRetrying(false);
    }
  };

  const firstSubject = quiz.subjects[0]?.slug || "all";
  const explainLink = `/learn/${quiz.subjects.length === 1 ? firstSubject : "all"}?q=${encodeURIComponent(
    `I answered these questions incorrectly. Please explain each one simply:\n${wrong.map((w) => `- ${quiz.questions[w.i].question}`).join("\n")}`,
  )}`;

  return (
    <div className="assessment">
      <Panel>
        <div className="score-summary">
          <Ring fraction={ratio} size={128} stroke={10} label={`${score}/${total}`} sub={`${Math.round(ratio * 100)}%`} />
          <div>
            <span className="eyebrow">{t("your_score")} · {quiz.subject_title}{quiz.completed_at ? ` · ${new Date(quiz.completed_at).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}` : ""}</span>
            <h2>{heading}</h2>
            <p className="muted" style={{ display: "flex", flexWrap: "wrap", gap: "4px 14px" }}>
              {finished?.xp_gained > 0 && <span>{t("xp_gained", { n: finished.xp_gained })}</span>}
              {finished?.duration_s != null && <span><Clock size={13} style={{ verticalAlign: "-2px" }} /> {formatTime(finished.duration_s)}</span>}
              <span style={{ textTransform: "capitalize" }}>{quiz.mode} mode</span>
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
              {wrong.length > 0 && <button className="btn" type="button" onClick={retry} disabled={retrying}><RotateCcw size={15} /> Retry my mistakes</button>}
              {wrong.length > 0 && <Link className="btn btn-secondary" to={explainLink}><MessageSquareText size={15} /> {t("explain_mistakes")}</Link>}
              <button className={`btn ${wrong.length ? "btn-ghost" : ""}`} type="button" onClick={onRestart}><Play size={15} /> {reviewing ? "Retake this assessment" : t("try_again")}</button>
              <a className="btn btn-ghost" href={`/print/assessment/${quiz.id}`} target="_blank" rel="noopener"><FileDown size={15} /> {t("export_pdf")}</a>
              <Link className="btn btn-ghost" to="/assessments/history"><History size={15} /> History</Link>
            </div>
            {error && <p className="form-error">{error}</p>}
          </div>
        </div>
      </Panel>

      {finished?.breakdown?.length > 1 && (
        <div className="section">
          <div className="section-head"><h2>By subject</h2></div>
          <Panel>
            <div className="subject-breakdown">
              {finished.breakdown.map((b) => (
                <div className="sb-row" key={b.subject}>
                  <span>{b.subject}</span>
                  <span className="sb-bar"><span style={{ width: `${(b.correct / b.total) * 100}%` }} /></span>
                  <span className="num" style={{ textAlign: "right" }}>{b.correct}/{b.total}</span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      )}

      <div className="section">
        <div className="section-head"><h2>{t("review")}</h2><span className="eyebrow">{wrong.length} to revisit</span></div>
        <Panel tight>
          {quiz.questions.map((q, i) => {
            const r = review[i];
            if (!r) return null;
            return (
              <div className="list-row" key={i} style={{ alignItems: "flex-start" }}>
                <span className={`tag ${r.correct ? "positive" : "negative"}`} style={{ marginTop: 2 }}>
                  {r.correct ? t("correct") : r.choice === null || r.choice === undefined ? "Skipped" : t("incorrect")}
                </span>
                <div className="grow">
                  <Markdown className="prose title" source={q.question} />
                  <div className="desc">
                    {!r.correct && r.choice != null && <>Your answer: <InlineMarkdown source={q.options[r.choice]} /> · </>}
                    Correct answer: <strong><InlineMarkdown source={q.options[r.answer_index]} /></strong>
                  </div>
                  {!r.correct && r.explanation && <div className="desc" style={{ marginTop: 4 }}><InlineMarkdown source={r.explanation} /></div>}
                </div>
              </div>
            );
          })}
        </Panel>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ page

export default function Assessments() {
  const { t, app } = useApp();
  const params = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // A retake started from the history page arrives ready to run.
  const [quiz, setQuiz] = useState(() => location.state?.quiz || null);
  const [outcome, setOutcome] = useState(null);
  const [run, setRun] = useState(0);
  const initialSubjects = app.subjects.some((s) => s.slug === params.slug) ? [params.slug] : app.subjects.slice(0, 1).map((s) => s.slug);

  useCrumbs([{ label: t("nav_quiz"), to: "/assessments" }, ...(quiz ? [{ label: quiz.subject_title }] : [])]);
  const shownSlug = useRef(params.slug);
  useEffect(() => {
    if (shownSlug.current === params.slug) return;
    shownSlug.current = params.slug;
    setQuiz(null);
    setOutcome(null);
  }, [params.slug]);
  useEffect(() => {
    if (location.state?.quiz) navigate(location.pathname, { replace: true, state: null });
  }, [location.pathname, location.state, navigate]);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [quiz, outcome]);

  const restart = () => { setQuiz(null); setOutcome(null); setRun((n) => n + 1); };

  if (quiz && outcome) {
    return <Results key={quiz.id} quiz={quiz} outcome={outcome} onRestart={restart} onRetry={(next) => { setOutcome(null); setQuiz(next); }} />;
  }
  if (quiz) {
    return (
      <>
        {quiz.notice && <div className="panel" style={{ marginBottom: 16, background: "var(--notice-tint)", borderColor: "transparent" }}>
          <div className="panel-body small">{quiz.notice}</div></div>}
        {quiz.mode === "practice"
          ? <PracticeRunner key={quiz.id} quiz={quiz} onFinish={setOutcome} />
          : <ExamRunner key={quiz.id} quiz={quiz} onFinish={setOutcome} />}
      </>
    );
  }
  return <Builder key={`${initialSubjects.join()}-${run}`} initialSubjects={initialSubjects} initialTopic={searchParams.get("topic") || ""} onStart={setQuiz} />;
}
