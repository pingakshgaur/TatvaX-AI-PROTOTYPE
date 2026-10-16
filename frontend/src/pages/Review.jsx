// Review deck: questions the learner got wrong come back on a widening schedule until mastered.
import { ArrowRight, Brain, Check, ClipboardCheck, Layers, PartyPopper, RotateCcw, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import SubjectArt from "../components/SubjectArt.jsx";
import { CountUp, EmptyState, InlineMarkdown, Loading, Markdown, PageHeader, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import useUndoableDelete from "../lib/useUndoableDelete.js";

const KEYS = ["A", "B", "C", "D"];
const BOXES = [
  ["New", "Again today", "var(--c-coral)"],
  ["1", "Tomorrow", "var(--c-saffron)"],
  ["2", "In 3 days", "var(--c-indigo)"],
  ["3", "In a week", "var(--c-teal)"],
  ["4", "In 2 weeks", "var(--c-plum)"],
  ["Mastered", "Learned", "var(--c-leaf)"],
];
const cardPath = (id) => `/api/review/${id}`;

function dueText(due) {
  const days = Math.round((new Date(`${due}T00:00`) - new Date(new Date().toDateString())) / 86400000);
  if (days <= 0) return "today";
  if (days === 1) return "tomorrow";
  return `in ${days} days`;
}

function Session({ cards, onDone }) {
  const { app, celebrate } = useApp();
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [tally, setTally] = useState({ right: 0, wrong: 0, xp: 0, mastered: 0 });
  const nextRef = useRef(null);
  const card = cards[index];
  const subject = app.subjects.find((s) => s.slug === card?.subject);

  useEffect(() => { if (result) nextRef.current?.focus(); }, [result]);

  const choose = async (choice) => {
    setBusy(true);
    try {
      const res = await api(`/api/review/${card.id}`, { method: "POST", body: { choice } });
      setResult({ ...res, choice });
      setTally((t) => ({ right: t.right + res.correct, wrong: t.wrong + !res.correct, xp: t.xp + res.xp_gained, mastered: t.mastered + res.mastered }));
      if (res.xp_gained) celebrate({ xp_gained: res.xp_gained });
    } finally {
      setBusy(false);
    }
  };

  const next = () => {
    if (index === cards.length - 1) onDone(tally);
    else { setIndex(index + 1); setResult(null); }
  };

  return (
    <div className="assessment">
      <div className="runner-top">
        <span className="eyebrow">Card {index + 1} of {cards.length}</span>
        <div className="meter" role="progressbar" aria-valuenow={Math.round(((index + (result ? 1 : 0)) / cards.length) * 100)} aria-valuemin={0} aria-valuemax={100}>
          <span style={{ width: `${((index + (result ? 1 : 0)) / cards.length) * 100}%` }} />
        </div>
        <span className="review-tally"><Check size={13} /> {tally.right} <X size={13} /> {tally.wrong}</span>
      </div>
      <Panel>
        <div className="review-card-head">
          {subject && <SubjectArt subject={subject} size={30} />}
          <span className="small muted">{card.subject_title || subject?.title}</span>
          <span className="review-box" style={{ "--tone": BOXES[card.box][2] }}>{card.box === 0 ? "New" : `Box ${card.box}`}</span>
        </div>
        <Markdown className="prose question-text" source={card.question} />
        <div className="answer-list" role="group" aria-label="Answers">
          {card.options.map((option, i) => {
            let state = "";
            if (result) {
              if (i === result.answer_index) state = "correct";
              else if (i === result.choice) state = "incorrect";
            }
            return (
              <button key={i} type="button" className={`answer ${state}`} disabled={Boolean(result) || busy} onClick={() => choose(i)}>
                <span className="key" aria-hidden="true">{KEYS[i]}</span>
                <InlineMarkdown source={option} />
                {state === "correct" && <Check className="result-icon ok" size={18} aria-label="Correct" />}
                {state === "incorrect" && <X className="result-icon bad" size={18} aria-label="Incorrect" />}
              </button>
            );
          })}
        </div>
        {result && (
          <>
            <div className={`explanation${result.correct ? "" : " incorrect"}`} role="status">
              <span className="eyebrow">
                {result.mastered ? "Mastered! This card is retired." : result.correct ? `Correct. See it again ${dueText(result.due)}.` : `Not quite. It will come back ${dueText(result.due)}.`}
              </span>
              {result.explanation && <Markdown source={result.explanation} />}
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
              <button ref={nextRef} className="btn" type="button" onClick={next}>
                {index === cards.length - 1 ? "Finish" : "Next card"} <ArrowRight size={15} />
              </button>
            </div>
          </>
        )}
      </Panel>
    </div>
  );
}

export default function Review() {
  const { t, app, user, notify, progressVersion } = useApp();
  const [deck, setDeck] = useState(null);
  const [all, setAll] = useState(null);
  const [subject, setSubject] = useState("");
  const [session, setSession] = useState(null);
  const [finished, setFinished] = useState(null);
  useCrumbs([{ label: t("nav_review") }]);

  const load = useCallback(() => {
    const query = subject ? `?subject=${encodeURIComponent(subject)}` : "";
    api(`/api/review${query}`).then(setDeck).catch((err) => notify(err.message, { kind: "error" }));
    api("/api/review/all").then((res) => setAll(res.cards)).catch(() => setAll([]));
  }, [subject, notify]);

  useEffect(() => { load(); }, [load, user?.id, progressVersion]);

  const positions = useRef(new Map());
  const hideCard = useCallback((card) => setAll((list) => {
    positions.current.set(card.id, list.findIndex((c) => c.id === card.id));
    return list.filter((c) => c.id !== card.id);
  }), []);
  const restoreCard = useCallback((card) => setAll((list) => {
    if (list.some((c) => c.id === card.id)) return list;
    const next = [...list];
    next.splice(Math.min(positions.current.get(card.id) ?? 0, next.length), 0, card);
    return next;
  }), []);
  const removeCard = useUndoableDelete({ hide: hideCard, restore: restoreCard, path: cardPath });

  if (session) {
    return <Session cards={session} onDone={(tally) => { setSession(null); setFinished(tally); load(); }} />;
  }
  if (!deck) return <Loading />;
  const { summary, cards } = deck;
  const max = Math.max(1, ...summary.boxes);

  return (
    <>
      <PageHeader eyebrow={t("group_practice")} title={t("nav_review")}
        lede="Questions you got wrong in assessments come back here. Answer them correctly and they return less often, until you have mastered them." />

      {finished && (
        <div className="review-finished" role="status">
          <PartyPopper size={22} />
          <div>
            <strong>Session complete: {finished.right} right, {finished.wrong} to practise again.</strong>
            <span className="small muted">{finished.xp ? `+${finished.xp} XP` : ""}{finished.mastered ? ` · ${finished.mastered} mastered` : ""}</span>
          </div>
          <button className="icon-btn" type="button" aria-label="Close" onClick={() => setFinished(null)}><X size={15} /></button>
        </div>
      )}

      <div className="review-hero">
        <div className="review-due">
          <Brain size={26} />
          <div>
            <b><CountUp value={summary.due} /></b>
            <span>{summary.due === 1 ? "card to review today" : "cards to review today"}</span>
          </div>
          <div className="review-actions">
            <select className="select" aria-label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} style={{ width: "auto" }}>
              <option value="">All subjects</option>
              {app.subjects.map((s) => <option key={s.slug} value={s.slug}>{s.title}</option>)}
            </select>
            <button className="btn btn-lg" type="button" disabled={!cards.length} onClick={() => { setFinished(null); setSession(cards); }}>
              <RotateCcw size={16} /> Start review
            </button>
          </div>
          {!cards.length && summary.total > 0 && (
            <span className="small muted">All caught up.{summary.next_due ? ` Next cards ${dueText(summary.next_due)}.` : ""}</span>
          )}
        </div>
        <div className="review-boxes" aria-label="Cards in each box">
          {BOXES.map(([label, when, tone], i) => (
            <div key={label} className="rb" style={{ "--tone": tone }}>
              <span className="rb-bar"><span style={{ height: `${(summary.boxes[i] / max) * 100}%` }} /></span>
              <b>{summary.boxes[i]}</b>
              <span className="rb-label">{label}</span>
              <span className="rb-when">{when}</span>
            </div>
          ))}
        </div>
      </div>

      {summary.total === 0 ? (
        <EmptyState icon={Layers} title="Your review deck is empty"
          action={<Link className="btn" to="/assessments"><ClipboardCheck size={15} /> Take an assessment</Link>}>
          When you get a question wrong in an assessment, it is added here so you can master it.
        </EmptyState>
      ) : (
        <section className="section">
          <div className="section-head"><h2>All cards</h2><span className="eyebrow">{summary.mastered} mastered of {summary.total}</span></div>
          <Panel tight>
            {(all || []).map((card) => (
              <div className="list-row" key={card.id} style={{ alignItems: "flex-start" }}>
                <span className="review-box" style={{ "--tone": BOXES[card.box][2], marginTop: 2 }}>{BOXES[card.box][0]}</span>
                <div className="grow">
                  <div className="title review-q"><InlineMarkdown source={card.question.replace(/\n+/g, " ")} /></div>
                  <span className="desc">{card.subject_title} · {card.box >= 5 ? "mastered" : `due ${dueText(card.due)}`} · reviewed {card.reviews} time{card.reviews === 1 ? "" : "s"}</span>
                </div>
                <button className="icon-btn" type="button" title="Remove card" aria-label="Remove card" onClick={() => removeCard(card, "Card removed")}>
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </Panel>
        </section>
      )}
    </>
  );
}
