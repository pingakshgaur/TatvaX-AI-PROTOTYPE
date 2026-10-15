import { ArrowRight, Check, MessageSquareText, Play, RotateCcw, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { Ring } from "../components/Charts.jsx";
import { useCrumbs } from "../components/Shell.jsx";
import { InlineMarkdown, Markdown, Meter, PageHeader, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { subjectCode } from "../lib/format.js";

const KEYS = ["A", "B", "C", "D"];

function Setup({ initialSubject, initialTopic, onStart }) {
  const { t, app, lang } = useApp();
  const [subject, setSubject] = useState(initialSubject);
  const [topic, setTopic] = useState(initialTopic);
  const [count, setCount] = useState(5);
  const [difficulty, setDifficulty] = useState("medium");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const start = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { quiz } = await api("/api/quiz", { method: "POST", body: { subject, topic, count, difficulty, language: lang } });
      onStart(quiz);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader eyebrow={t("group_practice")} title={t("quiz_title")} lede={t("quiz_sub")} />
      <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1fr)", maxWidth: 820 }}>
        <Panel title="Configure assessment">
          <form onSubmit={start}>
            <div className="field">
              <span className="label">{t("nav_subjects")}</span>
              <div className="option-grid" role="group" aria-label={t("nav_subjects")}>
                {app.subjects.map((s) => (
                  <button key={s.slug} type="button" className="option-card" aria-pressed={subject === s.slug} onClick={() => setSubject(s.slug)}>
                    <span className="subject-code" style={{ "--subject-color": s.color, minWidth: 34, height: 34, fontSize: 11 }}>{subjectCode(s.title)}</span>
                    {s.title}
                  </button>
                ))}
              </div>
            </div>
            <div className="field">
              <label className="label" htmlFor="quiz-topic">{t("topic_optional")}</label>
              <input className="input" id="quiz-topic" dir="auto" maxLength={80} value={topic}
                placeholder={t("topic_placeholder")} onChange={(e) => setTopic(e.target.value)} />
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 24 }}>
              <div className="field">
                <span className="label">{t("questions")}</span>
                <div className="segmented" role="group" aria-label={t("questions")}>
                  {[5, 10].map((n) => <button key={n} type="button" aria-pressed={count === n} onClick={() => setCount(n)}>{n}</button>)}
                </div>
              </div>
              <div className="field">
                <span className="label">{t("difficulty")}</span>
                <div className="segmented" role="group" aria-label={t("difficulty")}>
                  {["easy", "medium", "hard"].map((d) => (
                    <button key={d} type="button" aria-pressed={difficulty === d} onClick={() => setDifficulty(d)}>{t(d)}</button>
                  ))}
                </div>
              </div>
            </div>
            <p className="form-error" role="alert">{error}</p>
            <button className="btn btn-lg" type="submit" disabled={busy || !subject}>
              {busy ? <><span className="spinner" aria-hidden="true" /> {t("making_quiz")}</> : <><Play size={16} /> {t("start_quiz")}</>}
            </button>
          </form>
        </Panel>
      </div>
    </>
  );
}

function Runner({ quiz, onFinish }) {
  const { t } = useApp();
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const nextRef = useRef(null);
  const total = quiz.questions.length;
  const question = quiz.questions[index];

  useEffect(() => { if (result) nextRef.current?.focus(); }, [result]);

  const choose = async (choice) => {
    setBusy(true);
    setError("");
    try {
      const res = await api(`/api/quiz/${quiz.id}/answer`, { method: "POST", body: { index, choice } });
      setResult({ ...res, choice });
      setAnswers((list) => [...list, { ...res, choice }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const next = () => {
    if (index === total - 1) onFinish(answers, result.finished);
    else { setIndex(index + 1); setResult(null); }
  };

  return (
    <div className="assessment">
      <div className="assessment-progress">
        <span className="eyebrow">{t("question_of", { n: index + 1, total })}</span>
        <Meter value={(index + (result ? 1 : 0)) / total} label="Progress" />
        <span className="tag">{quiz.subject_title}</span>
      </div>
      <Panel>
        <Markdown className="prose question-text" source={question.question} />
        <div className="answer-list" role="group" aria-label="Answers">
          {question.options.map((option, i) => {
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
      </Panel>
    </div>
  );
}

function Results({ quiz, answers, finished, onRestart }) {
  const { t, celebrate } = useApp();
  const celebrated = useRef(false);
  const total = quiz.questions.length;
  const score = finished?.score ?? answers.filter((a) => a.correct).length;
  const ratio = score / total;
  const wrong = answers.map((a, i) => ({ ...a, i })).filter((a) => !a.correct);
  const heading = ratio === 1 ? t("great_job") : ratio >= 0.6 ? t("good_job") : t("keep_going");

  useEffect(() => {
    if (finished && !celebrated.current) {
      celebrated.current = true;
      celebrate(finished);
    }
  }, [celebrate, finished]);

  const explainLink = `/learn/${quiz.subject}?q=${encodeURIComponent(
    `I answered these assessment questions incorrectly. Please explain each one simply:\n${wrong.map((w) => `- ${quiz.questions[w.i].question}`).join("\n")}`,
  )}`;

  return (
    <div className="assessment">
      <Panel>
        <div className="score-summary">
          <Ring fraction={ratio} size={124} stroke={9} label={`${score}/${total}`} sub={`${Math.round(ratio * 100)}%`} />
          <div>
            <span className="eyebrow">{t("your_score")} · {quiz.subject_title}</span>
            <h2>{heading}</h2>
            {finished?.xp_gained > 0 && <p className="muted">{t("xp_gained", { n: finished.xp_gained })}</p>}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
              <button className="btn" type="button" onClick={onRestart}><RotateCcw size={15} /> {t("try_again")}</button>
              {wrong.length > 0 && <Link className="btn btn-secondary" to={explainLink}><MessageSquareText size={15} /> {t("explain_mistakes")}</Link>}
              <Link className="btn btn-ghost" to="/progress">{t("nav_progress")}</Link>
            </div>
          </div>
        </div>
      </Panel>

      <div className="section">
        <div className="section-head"><h2>{t("review")}</h2></div>
        <Panel tight>
          {quiz.questions.map((q, i) => {
            const a = answers[i];
            return (
              <div className="list-row" key={i} style={{ alignItems: "flex-start" }}>
                <span className={`tag ${a.correct ? "positive" : "negative"}`} style={{ marginTop: 2 }}>{a.correct ? t("correct") : t("incorrect")}</span>
                <div className="grow">
                  <Markdown className="prose title" source={q.question} />
                  <div className="desc">
                    {!a.correct && <>Your answer: <InlineMarkdown source={q.options[a.choice]} /> · </>}
                    Correct answer: <strong><InlineMarkdown source={q.options[a.answer_index]} /></strong>
                  </div>
                </div>
              </div>
            );
          })}
        </Panel>
      </div>
    </div>
  );
}

export default function Assessments() {
  const { t, app } = useApp();
  const params = useParams();
  const [searchParams] = useSearchParams();
  const [quiz, setQuiz] = useState(null);
  const [outcome, setOutcome] = useState(null);
  const [run, setRun] = useState(0);
  const initialSubject = app.subjects.some((s) => s.slug === params.slug) ? params.slug : app.subjects[0]?.slug;

  useCrumbs([{ label: t("nav_quiz"), to: "/assessments" }, ...(quiz ? [{ label: quiz.subject_title }] : [])]);

  useEffect(() => { setQuiz(null); setOutcome(null); }, [params.slug]);

  if (quiz && outcome) {
    return <Results quiz={quiz} answers={outcome.answers} finished={outcome.finished}
      onRestart={() => { setQuiz(null); setOutcome(null); setRun((n) => n + 1); }} />;
  }
  if (quiz) {
    return <Runner quiz={quiz} onFinish={(answers, finished) => setOutcome({ answers, finished })} />;
  }
  return <Setup key={`${initialSubject}-${run}`} initialSubject={initialSubject} initialTopic={searchParams.get("topic") || ""} onStart={setQuiz} />;
}
