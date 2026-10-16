// Translator: type or paste text and see it in any of TatvaX's 13 languages as you type.
import { ArrowLeftRight, Copy, History, MessageSquareText, Mic, Trash2, Volume2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import { PageHeader, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { canListen, listen, speak } from "../lib/voice.js";

const MAX = 3000;
const HISTORY_KEY = "tatvax.translations";

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch { return []; }
}

function saveHistory(items) {
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, 12))); } catch { /* storage unavailable */ }
}

export default function Translate() {
  const { t, app, lang, notify, languageInfo } = useApp();
  const navigate = useNavigate();
  useCrumbs([{ label: t("nav_translate") }]);

  const [text, setText] = useState("");
  const [source, setSource] = useState("auto");
  const [target, setTarget] = useState(lang === "en" ? "hi" : lang);
  const [result, setResult] = useState(null); // { text, source, engine }
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState(loadHistory);
  const [listening, setListening] = useState(false);
  const requestRef = useRef(0);
  const stopRef = useRef(null);

  const run = useCallback(async (value, from, to) => {
    const trimmed = value.trim();
    if (!trimmed) { setResult(null); setError(""); return; }
    const id = ++requestRef.current;
    setBusy(true);
    setError("");
    try {
      const res = await api("/api/translate", { method: "POST", body: { text: trimmed, source: from, target: to } });
      if (id !== requestRef.current) return; // a newer request is on its way
      setResult(res);
      setHistory((items) => {
        const next = [{ text: trimmed, result: res.text, source: res.source, target: to },
          ...items.filter((h) => !(h.text === trimmed && h.target === to))];
        saveHistory(next);
        return next.slice(0, 12);
      });
    } catch (err) {
      if (id === requestRef.current) setError(err.message);
    } finally {
      if (id === requestRef.current) setBusy(false);
    }
  }, []);

  // Translate as you type, after a short pause.
  useEffect(() => {
    const timer = setTimeout(() => run(text, source, target), 650);
    return () => clearTimeout(timer);
  }, [text, source, target, run]);

  const swap = () => {
    const from = source === "auto" ? result?.source || "en" : source;
    setSource(target);
    setTarget(from);
    if (result?.text) setText(result.text);
  };

  const say = (value, code) => speak(value, { langCode: code, serverLanguages: app.tts_languages })
    .catch(() => notify("No voice is available for this language on this device", { kind: "error" }));

  const dictate = () => {
    if (stopRef.current) { stopRef.current(); return; }
    if (!canListen) { notify(t("voice_unsupported"), { kind: "error" }); return; }
    const code = source === "auto" ? lang : source;
    try {
      setListening(true);
      stopRef.current = listen(languageInfo(code).speech, {
        onInterim: setText,
        onFinal: setText,
        onError: (code) => { if (code !== "no-speech" && code !== "aborted") notify(`Voice input error: ${code}`, { kind: "error" }); },
        onEnd: () => { stopRef.current = null; setListening(false); },
      });
    } catch {
      setListening(false);
    }
  };

  const detected = source === "auto" && result?.source ? languageInfo(result.source) : null;
  // Every language is listed on both sides, in two rows of chips.
  const chips = (value, onPick, includeAuto) => (
    <div className="lang-grid" role="group" aria-label={includeAuto ? "Translate from" : "Translate to"}>
      {includeAuto && (
        <button type="button" className="lang-chip auto" aria-pressed={value === "auto"}
          onClick={() => onPick("auto")}>Detect</button>
      )}
      {app.languages.map((l) => (
        <button key={l.code} type="button" className="lang-chip" aria-pressed={value === l.code}
          title={l.name} onClick={() => onPick(l.code)}>{l.native}</button>
      ))}
    </div>
  );

  return (
    <>
      <PageHeader eyebrow={t("group_practice")} title={t("nav_translate")}
        lede="Translate study questions, answers and notes between 13 Indian languages. Results appear as you type." />

      <div className="translator">
        <section className="tr-pane" aria-label="Text to translate">
          <div className="tr-head">{chips(source, setSource, true)}</div>
          <div className="tr-body">
            <label className="sr-only" htmlFor="tr-input">Text to translate</label>
            <textarea id="tr-input" dir="auto" maxLength={MAX} placeholder="Type or paste text…" value={text}
              onChange={(e) => setText(e.target.value)} autoFocus />
          </div>
          <div className="tr-foot">
            {detected && <span className="detected">Detected: {detected.native}</span>}
            <span className="spacer" />
            <span className="mono">{text.length}/{MAX}</span>
            <button className={`icon-btn mic${listening ? " listening" : ""}`} type="button" onClick={dictate} aria-label="Speak the text" aria-pressed={listening}><Mic size={16} /></button>
            {text && <button className="icon-btn" type="button" onClick={() => say(text, result?.source || (source === "auto" ? "en" : source))} aria-label={t("listen")}><Volume2 size={16} /></button>}
            {text && <button className="icon-btn" type="button" onClick={() => setText("")} aria-label="Clear"><X size={16} /></button>}
          </div>
        </section>

        <div className="tr-swap"><button type="button" onClick={swap} aria-label="Swap languages" title="Swap languages"><ArrowLeftRight size={17} /></button></div>

        <section className="tr-pane" aria-label="Translation" aria-live="polite">
          <div className="tr-head">{chips(target, setTarget, false)}</div>
          <div className="tr-body">
            <div className={`tr-output${result?.text ? "" : " placeholder"}`} dir="auto">
              {error ? <span style={{ color: "var(--negative)" }}>{error}</span>
                : result?.text || (busy ? "Translating…" : "Translation appears here")}
            </div>
          </div>
          <div className="tr-foot">
            {busy && <span className="spinner" aria-hidden="true" />}
            {result?.engine && !busy && <span>{result.engine === "ai" ? "AI translation" : "Web translation"}</span>}
            <span className="spacer" />
            {result?.text && (
              <>
                <button className="icon-btn" type="button" onClick={() => say(result.text, target)} aria-label={t("listen")}><Volume2 size={16} /></button>
                <button className="icon-btn" type="button" aria-label={t("copy")}
                  onClick={() => navigator.clipboard.writeText(result.text).then(() => notify(t("copied")))}><Copy size={16} /></button>
                <button className="btn btn-sm" type="button" onClick={() => navigate(`/learn/all?q=${encodeURIComponent(result.text)}`)}>
                  <MessageSquareText size={14} /> Ask the tutor
                </button>
              </>
            )}
          </div>
        </section>
      </div>

      {history.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}><History size={18} /> Recent</h2>
            <button className="btn btn-ghost btn-sm" type="button" onClick={() => { setHistory([]); saveHistory([]); }}><Trash2 size={14} /> Clear</button>
          </div>
          <Panel tight>
            <div className="tr-history" style={{ padding: 12 }}>
              {history.map((h, i) => (
                <button key={i} type="button" onClick={() => { setSource(h.source || "auto"); setTarget(h.target); setText(h.text); }}>
                  <span dir="auto">{h.text}</span><span dir="auto">{h.result}</span>
                </button>
              ))}
            </div>
          </Panel>
        </section>
      )}
    </>
  );
}
