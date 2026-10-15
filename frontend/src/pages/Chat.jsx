import {
  ArrowUp, ClipboardCheck, Copy, CornerDownRight, Languages, Mic, PanelLeft, Plus, Sparkles, Square, Trash2, Volume2, X,
} from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import { Dialog, EmptyState, Markdown } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api, ApiError, streamChat } from "../lib/api.js";
import { subjectCode, timeAgo } from "../lib/format.js";
import { SUGGESTIONS } from "../lib/i18n.js";
import { plainText } from "../lib/markdown.js";
import { canListen, listen, speak, stopSpeaking } from "../lib/voice.js";

const CHIP_COLORS = ["var(--c-teal)", "var(--c-indigo)", "var(--c-coral)"];

const MIC_ERRORS = {
  "not-allowed": "Microphone access is blocked. Allow it from the icon in the browser's address bar, then try again.",
  "service-not-allowed": "This browser doesn't allow speech recognition here. Try Chrome or Edge.",
  "audio-capture": "No microphone was found. Check that one is connected.",
  network: "Voice recognition needs an internet connection: Chrome and Edge send speech to their speech service.",
  "language-not-supported": "Voice input isn't available for this language in this browser yet.",
};

function TranslateAnswer({ text, onClose }) {
  const { app, lang, languageInfo } = useApp();
  const [open, setOpen] = useState(false);
  const [result, setResult] = useState(null);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const close = (event) => { if (!ref.current?.contains(event.target)) setOpen(false); };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);

  const translate = async (target) => {
    setOpen(false);
    setResult({ target, text: null });
    try {
      const res = await api("/api/translate", { method: "POST", body: { text: text.slice(0, 3000), source: "auto", target } });
      setResult({ target, text: res.text });
    } catch (err) {
      setResult({ target, error: err.message });
    }
  };

  return (
    <>
      <span ref={ref} style={{ position: "relative" }}>
        <button className="icon-btn" type="button" aria-label="Translate this answer" title="Translate this answer"
          aria-expanded={open} onClick={() => setOpen((v) => !v)}><Languages size={16} /></button>
        {open && (
          <div className="lang-menu" role="menu">
            {app.languages.filter((l) => l.code !== lang).map((l) => (
              <button key={l.code} type="button" role="menuitem" onClick={() => translate(l.code)}>{l.native} <span className="muted">· {l.name}</span></button>
            ))}
          </div>
        )}
      </span>
      {result && (
        <div className="inline-translation" style={{ flexBasis: "100%" }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: 6 }}>
            <span className="eyebrow">{languageInfo(result.target).native}</span>
            <button className="icon-btn" type="button" style={{ marginLeft: "auto" }} aria-label="Close translation"
              onClick={() => { setResult(null); onClose?.(); }}><X size={14} /></button>
          </div>
          {result.error ? <p className="form-error">{result.error}</p>
            : result.text === null ? <span className="spinner" aria-label="Translating" />
              : <Markdown source={result.text} />}
        </div>
      )}
    </>
  );
}

function AssistantTurn({ message, canAssess, onAssess, showSuggestions, onAsk }) {
  const { t, lang, app, notify } = useApp();
  const [speaking, setSpeaking] = useState(false);

  const toggleSpeech = () => {
    if (speaking) { stopSpeaking(); return; }
    setSpeaking(true);
    speak(plainText(message.content), { langCode: lang, serverLanguages: app.tts_languages })
      .catch(() => notify("No voice is available for this language on this device", { kind: "error" }))
      .finally(() => setSpeaking(false));
  };

  return (
    <article className="turn turn-assistant">
      <div className="turn-label">TatvaX</div>
      <div className="turn-body">
        {message.pending && !message.content
          ? <span className="typing" aria-label="TatvaX is writing"><span /><span /><span /></span>
          : <Markdown source={message.content} />}
        {message.error && <p style={{ color: "var(--negative)" }}>{message.error}</p>}
        {message.stopped && <p className="small muted">Response stopped.</p>}
        {!message.pending && message.content && (
          <div className="turn-footer">
            <span className={`tag ${message.engine === "ai" ? "primary" : ""}`}>
              {message.engine === "ai" ? t("ai_badge") : t("library_badge")}
            </span>
            <span className="spacer" />
            <button className="icon-btn" type="button" onClick={toggleSpeech} aria-label={t("listen")} title={t("listen")}>
              {speaking ? <Square size={15} /> : <Volume2 size={16} />}
            </button>
            <button className="icon-btn" type="button" aria-label={t("copy")} title={t("copy")}
              onClick={() => navigator.clipboard.writeText(message.content).then(() => notify(t("copied")))}>
              <Copy size={15} />
            </button>
            <TranslateAnswer text={message.content} />
            {canAssess && message.question && (
              <button className="icon-btn" type="button" aria-label={t("quiz_me")} title={t("quiz_me")} onClick={() => onAssess(message.question)}>
                <ClipboardCheck size={16} />
              </button>
            )}
            {message.sources?.length > 0 && (
              <div className="sources"><b>Sources</b>{message.sources.join(" · ")}</div>
            )}
          </div>
        )}
        {showSuggestions && message.suggestions?.length > 0 && (
          <div className="suggestions" aria-label="Suggested follow-up questions">
            <span className="eyebrow"><Sparkles size={13} /> Keep exploring</span>
            {message.suggestions.map((s, i) => (
              <button key={s} type="button" className="suggestion-chip" style={{ "--chip": CHIP_COLORS[i % 3], "--i": i }} onClick={() => onAsk(s)}>
                <CornerDownRight size={15} aria-hidden="true" /> <span dir="auto">{s}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}

// Live microphone level, shown while listening so students can see TatvaX hears them.
function useMicLevel(active) {
  const [levels, setLevels] = useState([0, 0, 0, 0, 0]);
  useEffect(() => {
    if (!active || !navigator.mediaDevices?.getUserMedia) return undefined;
    let stream, ctx, frame, stopped = false;
    navigator.mediaDevices.getUserMedia({ audio: true }).then((s) => {
      if (stopped) { s.getTracks().forEach((track) => track.stop()); return; }
      stream = s;
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      ctx.createMediaStreamSource(stream).connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        setLevels([2, 5, 9, 14, 20].map((i) => Math.min(1, data[i] / 200)));
        frame = requestAnimationFrame(tick);
      };
      tick();
    }).catch(() => {});
    return () => {
      stopped = true;
      cancelAnimationFrame(frame);
      stream?.getTracks().forEach((track) => track.stop());
      ctx?.close();
    };
  }, [active]);
  return levels;
}

export default function Chat({ mode }) {
  const { t, app, lang, languageInfo, notify, celebrate, user } = useApp();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const slug = mode === "subject" ? params.slug : app.helpdesk?.slug;
  const subject = mode === "subject" ? app.subjects.find((s) => s.slug === slug) : app.helpdesk;
  const conversationId = Number(params.conversationId) || null;
  const base = mode === "helpdesk" ? "/helpdesk" : `/learn/${slug}`;
  const title = mode === "helpdesk" ? t("card_helpdesk") : subject ? subject.title : t("all_subjects");
  const suggestionKey = mode === "helpdesk" ? "helpdesk" : SUGGESTIONS[slug] ? slug : "all";
  const invalidSubject = mode === "subject" && slug !== "all" && !subject;

  useCrumbs(mode === "helpdesk"
    ? [{ label: t("nav_helpdesk") }]
    : [{ label: t("nav_subjects"), to: "/subjects" }, { label: title }]);

  const [conversations, setConversations] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);

  const threadRef = useRef(null);
  const textareaRef = useRef(null);
  const controllerRef = useRef(null);
  const stopListeningRef = useRef(null);
  const createdIdRef = useRef(null);
  const stickRef = useRef(true);
  const bufferRef = useRef({ text: "", frame: 0 });
  const initialSent = useRef(false);

  const loadHistory = useCallback(async () => {
    const query = new URLSearchParams({ mode });
    if (mode === "subject") query.set("subject", slug);
    const { conversations: list } = await api(`/api/conversations?${query}`).catch(() => ({ conversations: [] }));
    setConversations(list);
  }, [mode, slug]);

  useEffect(() => { loadHistory(); }, [loadHistory, user?.id]);

  // Load the selected conversation (unless we just created it while streaming).
  useEffect(() => {
    setHistoryOpen(false);
    if (!conversationId) {
      if (!controllerRef.current) setMessages([]);
      return;
    }
    if (conversationId === createdIdRef.current) {
      createdIdRef.current = null; // the streamed messages are already on screen
      return;
    }
    let live = true;
    api(`/api/conversations/${conversationId}`)
      .then(({ messages: rows }) => {
        if (!live) return;
        let lastQuestion = "";
        setMessages(rows.map((m) => {
          if (m.role === "user") lastQuestion = m.content;
          return { id: m.id, role: m.role, content: m.content, engine: m.engine, suggestions: m.suggestions,
            question: m.role === "assistant" ? lastQuestion : undefined };
        }));
        stickRef.current = true;
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) navigate(base, { replace: true });
        else notify(err.message, { kind: "error" });
      });
    return () => { live = false; };
  }, [conversationId, base, navigate, notify]);

  useLayoutEffect(() => {
    const el = threadRef.current;
    if (el && stickRef.current) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => () => {
    controllerRef.current?.abort();
    stopListeningRef.current?.();
    stopSpeaking();
  }, []);

  const updateLast = (patch) => setMessages((list) => {
    const next = [...list];
    next[next.length - 1] = { ...next[next.length - 1], ...patch };
    return next;
  });

  const send = useCallback(async (raw) => {
    const text = raw.trim();
    if (!text || controllerRef.current) return;
    stopSpeaking();
    setInput("");
    stickRef.current = true;
    setMessages((list) => [...list, { role: "user", content: text }, { role: "assistant", content: "", pending: true, question: text }]);

    const controller = new AbortController();
    controllerRef.current = controller;
    setBusy(true);
    bufferRef.current = { text: "", frame: 0 };
    const flush = () => {
      bufferRef.current.frame = 0;
      updateLast({ content: bufferRef.current.text });
    };
    const schedule = () => { if (!bufferRef.current.frame) bufferRef.current.frame = requestAnimationFrame(flush); };

    try {
      await streamChat({
        message: text, mode, subject: mode === "subject" ? slug : undefined,
        language: lang, conversation_id: conversationId || createdIdRef.current || null,
      }, (event) => {
        if (event.type === "start") {
          if (!conversationId && createdIdRef.current !== event.conversation_id) {
            createdIdRef.current = event.conversation_id;
            navigate(`${base}/${event.conversation_id}`, { replace: true });
          }
        } else if (event.type === "delta") {
          bufferRef.current.text += event.text;
          schedule();
        } else if (event.type === "replace") {
          bufferRef.current.text = event.text;
          schedule();
        } else if (event.type === "done") {
          cancelAnimationFrame(bufferRef.current.frame);
          updateLast({ content: bufferRef.current.text, pending: false, engine: event.engine, sources: event.sources,
            suggestions: event.suggestions });
          celebrate(event);
          loadHistory();
        } else if (event.type === "error") {
          updateLast({ pending: false, error: event.message });
        }
      }, controller.signal);
    } catch (err) {
      cancelAnimationFrame(bufferRef.current.frame);
      if (err.name === "AbortError") {
        updateLast({ content: bufferRef.current.text, pending: false, stopped: true });
      } else {
        setMessages((list) => list.slice(0, -2));
        setInput(text);
        notify(err.message, { kind: "error" });
      }
    } finally {
      controllerRef.current = null;
      setBusy(false);
      textareaRef.current?.focus();
    }
  }, [base, celebrate, conversationId, lang, loadHistory, mode, navigate, notify, slug]);

  // A question passed from the overview page (?q=) is sent once.
  useEffect(() => {
    const q = searchParams.get("q");
    if (q && !initialSent.current && !conversationId) {
      initialSent.current = true;
      setSearchParams({}, { replace: true });
      send(q);
    }
  }, [conversationId, searchParams, send, setSearchParams]);

  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [input]);

  const micLevels = useMicLevel(listening);

  const toggleMic = async () => {
    if (stopListeningRef.current) { stopListeningRef.current(); return; }
    if (!canListen) { notify(t("voice_unsupported"), { kind: "error", duration: 6000 }); return; }
    if (!window.isSecureContext) {
      notify("Voice input needs a secure (https) connection.", { kind: "error", duration: 6000 });
      return;
    }
    stopSpeaking();
    // Ask for the microphone first, so the browser shows its permission prompt and we can
    // explain a refusal clearly instead of failing silently.
    if (navigator.mediaDevices?.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((track) => track.stop());
      } catch (err) {
        const code = err.name === "NotFoundError" ? "audio-capture" : "not-allowed";
        notify(MIC_ERRORS[code], { kind: "error", duration: 7000 });
        return;
      }
    }
    try {
      setListening(true);
      let heard = false;
      stopListeningRef.current = listen(languageInfo().speech, {
        onInterim: (text) => { heard = true; setInput(text); },
        onFinal: (text) => send(text),
        onError: (code) => {
          if (code === "no-speech") notify("I didn't hear anything. Tap the microphone and speak clearly.", { duration: 5000 });
          else if (code !== "aborted") notify(MIC_ERRORS[code] || `Voice input stopped (${code}).`, { kind: "error", duration: 7000 });
        },
        onEnd: () => {
          stopListeningRef.current = null;
          setListening(false);
          if (!heard) textareaRef.current?.focus();
        },
      });
    } catch {
      setListening(false);
      notify(t("voice_unsupported"), { kind: "error" });
    }
  };

  const confirmDelete = async () => {
    const id = pendingDelete.id;
    setPendingDelete(null);
    try {
      await api(`/api/conversations/${id}`, { method: "DELETE" });
      if (id === conversationId) navigate(base);
      loadHistory();
    } catch (err) {
      notify(err.message, { kind: "error" });
    }
  };

  if (invalidSubject) {
    return <div className="page"><EmptyState title="Subject not found" action={<Link className="btn" to="/subjects">{t("nav_subjects")}</Link>} /></div>;
  }

  return (
    <div className={`chat${navigator.onLine ? "" : " has-offline-bar"}`}>
      <aside className={`chat-history${historyOpen ? " open" : ""}`} aria-label={t("history")}>
        <div className="chat-history-head">
          <Link className="btn btn-block" to={base} onClick={() => {
            controllerRef.current?.abort();
            createdIdRef.current = null;
            setMessages([]);
            setInput("");
          }}><Plus size={16} /> {t("new_chat")}</Link>
          <span className="eyebrow">{t("history")}</span>
        </div>
        <ul className="chat-history-list">
          {conversations.length === 0 && <li className="small muted" style={{ padding: "8px 14px" }}>{t("no_history")}</li>}
          {conversations.map((c) => (
            <li key={c.id} className={`history-item${c.id === conversationId ? " active" : ""}`}>
              <Link to={`${base}/${c.id}`} title={c.title}>
                <span className="t">{c.title}</span>
                <span className="d">{timeAgo(c.updated_at)}</span>
              </Link>
              <button className="icon-btn" type="button" aria-label={`${t("delete")}: ${c.title}`} onClick={() => setPendingDelete(c)}>
                <Trash2 size={15} />
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="chat-main">
        <header className="chat-header">
          <button className="icon-btn bordered history-toggle" type="button" aria-label={t("history")}
            aria-expanded={historyOpen} onClick={() => setHistoryOpen((open) => !open)}><PanelLeft size={16} /></button>
          <span className="subject-code" style={{ "--subject-color": subject?.color || "var(--accent)", minWidth: 38, height: 38 }}>
            {mode === "helpdesk" ? "HLP" : subject ? subjectCode(subject.title) : "ALL"}
          </span>
          <div className="grow">
            <h1>{title}</h1>
            <span className="small muted">{app.ai_enabled ? t("ai_badge") : t("library_badge")} · {languageInfo().native}</span>
          </div>
          {mode === "subject" && subject && (
            <Link className="btn btn-secondary btn-sm" to={`/assessments/${slug}`} aria-label={t("nav_quiz")}><ClipboardCheck size={15} /> <span>{t("nav_quiz")}</span></Link>
          )}
        </header>

        <div className="thread" ref={threadRef}
          onScroll={(e) => { const el = e.currentTarget; stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80; }}>
          <div className="thread-inner" aria-live="polite">
            {messages.length === 0 ? (
              <div className="chat-start">
                <span className="eyebrow">{mode === "helpdesk" ? t("nav_helpdesk") : t("card_learn")}</span>
                <h2>{title}</h2>
                <p>{mode === "helpdesk" ? t("welcome_helpdesk") : t("welcome_subject", { subject: title })}</p>
                <div className="eyebrow" style={{ marginTop: 22 }}>{t("try_asking")}</div>
                <div className="prompt-list">
                  {SUGGESTIONS[suggestionKey].map((s) => (
                    <button key={s} type="button" onClick={() => send(s)}><CornerDownRight size={15} aria-hidden="true" /> {s}</button>
                  ))}
                </div>
              </div>
            ) : messages.map((m, i) => (m.role === "user" ? (
              <article className="turn turn-user" key={m.id ?? `u${i}`}>
                <div className="turn-label">{t("you")}</div>
                <div className="turn-body" dir="auto">{m.content}</div>
              </article>
            ) : (
              <AssistantTurn key={m.id ?? `a${i}`} message={m} canAssess={mode === "subject" && Boolean(subject)}
                showSuggestions={i === messages.length - 1 && !busy} onAsk={send}
                onAssess={(q) => navigate(`/assessments/${slug}?topic=${encodeURIComponent(q.slice(0, 80))}`)} />
            )))}
          </div>
        </div>

        <div className="composer">
          {listening && (
            <div className="listening-banner" role="status">
              <span className="mic-meter" aria-hidden="true">{micLevels.map((v, i) => <span key={i} style={{ height: `${4 + v * 14}px` }} />)}</span>
              {t("listening")}
              <button className="btn btn-sm btn-danger" type="button" style={{ marginLeft: "auto" }} onClick={() => stopListeningRef.current?.()}>
                <Square size={12} /> {t("stop")}
              </button>
            </div>
          )}
          <form className="composer-box" onSubmit={(e) => { e.preventDefault(); if (busy) controllerRef.current?.abort(); else send(input); }}>
            <label className="sr-only" htmlFor="composer-input">{t("ask_placeholder")}</label>
            <textarea id="composer-input" ref={textareaRef} rows={1} dir="auto" maxLength={2000}
              placeholder={listening ? t("listening") : t("ask_placeholder")} value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(input); }
              }} />
            <div className="composer-tools">
              <button className={`icon-btn bordered mic${listening ? " listening" : ""}`} type="button" onClick={toggleMic}
                aria-label={t("voice_input")} title={t("voice_input")} aria-pressed={listening}><Mic size={16} /></button>
              <span className="spacer" />
              <span className="hint">{t("enter_to_send")}</span>
              <button className="btn btn-sm" type="submit" disabled={!busy && !input.trim()} aria-label={busy ? t("stop") : t("send")}>
                {busy ? <><Square size={13} /> {t("stop")}</> : <><ArrowUp size={15} /> {t("send")}</>}
              </button>
            </div>
          </form>
          <p className="composer-note">{t("composer_note")}</p>
        </div>
      </section>

      <Dialog open={Boolean(pendingDelete)} onClose={() => setPendingDelete(null)} title="Delete session">
        <p>Delete “{pendingDelete?.title}”? This can't be undone.</p>
        <div className="dialog-footer">
          <button className="btn btn-secondary" type="button" onClick={() => setPendingDelete(null)}>{t("cancel")}</button>
          <button className="btn btn-danger" type="button" onClick={confirmDelete}><Trash2 size={15} /> {t("delete")}</button>
        </div>
      </Dialog>
    </div>
  );
}
