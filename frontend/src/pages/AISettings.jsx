// Teacher console, AI settings: choose which AI provider powers TatvaX and manage each one's
// API key and model. Every provider keeps its own key, so switching back and forth is instant.
import {
  CheckCircle2, Copy, Cpu, ExternalLink, Eye, EyeOff, KeyRound, RefreshCw, Save, Server, Trash2, XCircle, Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Loading, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";
import { timeAgo } from "../lib/format.js";

// Providers with a free tier (or, for Ollama, no cost at all).
const FREE = new Set(["nvidia", "gemini", "groq", "openrouter", "mistral", "ollama"]);

const ABOUT = {
  nvidia: "Free developer tier. Nemotron, Llama, Gemma and more.",
  gemini: "Free tier from Google AI Studio. Fast Gemini Flash models.",
  groq: "Free tier. Very fast open models.",
  openrouter: "One key for hundreds of models, including free ones.",
  openai: "GPT models. Paid, pay as you go.",
  anthropic: "Claude models. Paid, pay as you go.",
  mistral: "Mistral models, with a free experiment tier.",
  deepseek: "DeepSeek chat models at a low cost.",
  together: "Open models hosted by Together AI.",
  xai: "Grok models from xAI.",
  ollama: "Runs models on this computer. No key, works offline.",
  custom: "Any OpenAI-compatible server, such as LM Studio or vLLM.",
};

const STEPS = {
  nvidia: [
    <>Go to <b>build.nvidia.com</b> and sign in, or create a free NVIDIA account.</>,
    <>Open your profile menu, choose <b>API Keys</b>, then <b>Generate API Key</b>.</>,
    <>Copy the key (it starts with <code>nvapi-</code>), paste it here and select <b>Save</b>.</>,
  ],
  gemini: [<>Open <b>Google AI Studio</b> and sign in with a Google account.</>, <>Choose <b>Get API key</b>, then <b>Create API key</b>.</>, <>Paste the key here and select <b>Save</b>.</>],
  groq: [<>Sign in to the <b>Groq console</b>.</>, <>Open <b>API Keys</b> and create a key (it starts with <code>gsk_</code>).</>, <>Paste it here and select <b>Save</b>.</>],
  ollama: [<>Install <b>Ollama</b> on the computer that runs TatvaX.</>, <>Run <code>ollama pull llama3.2</code> (or any model) once.</>, <>Select <b>Save</b>, then <b>Load available models</b>.</>],
  custom: [<>Start your OpenAI-compatible server.</>, <>Enter its address, ending in <code>/v1</code>, and a key if it needs one.</>, <>Select <b>Save</b>, then <b>Load available models</b>.</>],
};

function statusOf(p, allowed) {
  if (!allowed) return ["negative", "Off on the server"];
  if (!p.configured) return ["", "Not set up"];
  if (!p.available) return ["negative", "Key rejected"];
  return ["positive", p.active ? "In use" : "Ready"];
}

function ProviderPanel({ provider: p, allowed, recommended, onChanged }) {
  const { notify, reloadApp } = useApp();
  const [key, setKey] = useState("");
  const [model, setModel] = useState("");
  const [customModel, setCustomModel] = useState("");
  const [baseUrl, setBaseUrl] = useState(p.base_url || "");
  const [live, setLive] = useState(null);
  const [revealed, setRevealed] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [testResult, setTestResult] = useState(null);
  const isNvidia = p.id === "nvidia";
  const curated = p.models.length ? p.models : isNvidia ? recommended : [];
  const choices = [...curated, ...(live || []).filter((id) => !curated.some((m) => m.id === id)).map((id) => ({ id, name: id, note: "" }))];

  useEffect(() => {
    const known = choices.some((m) => m.id === p.model);
    setModel(p.model ? (known ? p.model : "custom") : choices[0]?.id || "custom");
    setCustomModel(p.model && !known ? p.model : "");
    setBaseUrl(p.base_url || "");
  }, [p.id, p.model, p.base_url, live]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { setKey(""); setRevealed(null); setLive(null); setError(""); setTestResult(null); }, [p.id]);

  const fetchKey = async () => (await api(`/api/admin/ai/key?provider=${p.id}`)).api_key;
  const reveal = async () => {
    if (revealed) { setRevealed(null); return; }
    try { setRevealed(await fetchKey()); } catch (err) { setError(err.message); }
  };
  const copyKey = async () => {
    try {
      await navigator.clipboard.writeText(revealed || (await fetchKey()));
      notify("API key copied");
    } catch (err) {
      setError(err.message);
    }
  };

  const test = async () => {
    setError("");
    setBusy("test");
    try {
      const result = await api("/api/admin/ai/test", { method: "POST", body: { provider: p.id } });
      setTestResult({ ok: true, text: `Connected in ${(result.latency_ms / 1000).toFixed(1)} s. ${result.provider?.model || p.model} replied: “${result.reply}”` });
    } catch (err) {
      setTestResult({ ok: false, text: err.message });
    } finally {
      setBusy("");
      onChanged(await api("/api/admin/ai").catch(() => null));
      reloadApp().catch(() => {});
    }
  };

  const save = async (body, message) => {
    setError("");
    setTestResult(null);
    setBusy(body.activate && Object.keys(body).length === 2 ? "activate" : "save");
    try {
      const data = await api("/api/admin/ai", { method: "PUT", body: { provider: p.id, ...body } });
      onChanged(data);
      setKey("");
      setRevealed(null);
      await reloadApp();
      notify(message, { kind: "success" });
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setBusy("");
    }
  };

  const loadModels = async () => {
    setError("");
    setBusy("models");
    try {
      const { models } = await api(`/api/admin/ai/models?provider=${p.id}`);
      setLive(models);
      notify(`${models.length} model${models.length === 1 ? "" : "s"} available`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  };

  const submit = async (event, activate = false) => {
    event?.preventDefault();
    const body = {};
    const chosen = model === "custom" ? customModel.trim() : model;
    if (chosen && chosen !== p.model) body.model = chosen;
    const newKey = key.trim();
    if (newKey) body.api_key = newKey;
    if ((p.needs_base_url || p.id === "ollama") && baseUrl.trim() !== (p.base_url || "")) body.base_url = baseUrl.trim();
    if (activate) body.activate = true;
    const saved = await save(body, activate ? `${p.name} is now powering TatvaX` : newKey ? `${p.name} API key saved` : "AI settings saved");
    const after = saved?.providers.find((x) => x.id === p.id);
    if (after?.configured && (newKey || activate)) test(); // check a new key straight away
  };

  const [statusKind, statusLabel] = statusOf(p, allowed);
  const selected = choices.find((m) => m.id === model);
  const hint = p.key_hint || "";

  return (
    <Panel title={<span className="ai-panel-title">{p.name}{FREE.has(p.id) && <span className="tag positive">Free tier</span>}</span>}
      actions={<span className={`tag ${statusKind}`}>{statusLabel}</span>}>
      <p className="small muted" style={{ marginTop: 0 }}>{ABOUT[p.id]}</p>
      {p.configured && p.needs_key !== false && hint && (
        <div className="key-card" style={p.available ? undefined : { background: "var(--negative-tint)", borderColor: "var(--negative)" }}>
          <span className="key-icon" style={p.available ? undefined : { background: "var(--negative)" }}><KeyRound size={17} /></span>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="kc-meta">{p.source === "environment" ? "Key from the server's environment settings" : "Saved key"}
              {p.saved_at && p.source === "settings" ? ` · saved ${timeAgo(p.saved_at)}` : ""}</div>
            <code>{revealed || `${hint.split("…")[0] ?? ""}${"•".repeat(24)}${hint.split("…")[1] ?? ""}`}</code>
          </div>
          <button className="icon-btn" type="button" onClick={reveal} aria-label={revealed ? "Hide key" : "Show key"} title={revealed ? "Hide key" : "Show key"}>
            {revealed ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
          <button className="icon-btn" type="button" onClick={copyKey} aria-label="Copy key" title="Copy key"><Copy size={16} /></button>
        </div>
      )}

      <form onSubmit={(e) => submit(e)} noValidate>
        {(p.needs_base_url || p.id === "ollama") && (
          <div className="field">
            <label className="label" htmlFor={`ai-url-${p.id}`}><Server size={13} /> Server address</label>
            <input className="input mono" id={`ai-url-${p.id}`} spellCheck={false} value={baseUrl}
              placeholder={p.id === "ollama" ? "http://localhost:11434/v1" : "http://localhost:1234/v1"} onChange={(e) => setBaseUrl(e.target.value)} />
          </div>
        )}
        {p.needs_key !== false && (
          <div className="field">
            <label className="label" htmlFor={`ai-key-${p.id}`}>{p.configured ? "Replace the key" : `${p.name} API key`}{p.id === "custom" ? " (if your server needs one)" : ""}</label>
            <input className="input mono" id={`ai-key-${p.id}`} type="password" autoComplete="off" spellCheck={false}
              placeholder={hint ? `Saved: ${hint} (enter a new key to replace it)` : p.key_prefix ? `${p.key_prefix}...` : "Paste your API key"}
              value={key} onChange={(e) => setKey(e.target.value)} />
            <span className="hint">
              {p.source === "environment"
                ? "Currently using a key from the server's environment. A key saved here takes priority."
                : "Stored only on this server. It is never sent to students' browsers."}
            </span>
          </div>
        )}
        <div className="field">
          <label className="label" htmlFor={`ai-model-${p.id}`}>Model</label>
          <div className="model-row">
            <select className="select" id={`ai-model-${p.id}`} value={model} onChange={(e) => setModel(e.target.value)}>
              {choices.map((m) => <option key={m.id} value={m.id}>{m.name === m.id ? m.id : `${m.name} (${m.id})`}</option>)}
              <option value="custom">Another model…</option>
            </select>
            <button className="btn btn-secondary btn-sm" type="button" onClick={loadModels} disabled={!p.configured || Boolean(busy)}
              title={p.configured ? "Ask the provider which models this key can use" : "Save a key first"}>
              {busy === "models" ? <span className="spinner" aria-hidden="true" /> : <RefreshCw size={14} />} Load available models
            </button>
          </div>
          {selected?.note && <span className="hint">{selected.note}</span>}
          {live && <span className="hint">{live.length} models are available with this key.</span>}
          {model === "custom" && (
            <input className="input mono" style={{ marginTop: 8 }} aria-label="Model ID" placeholder={isNvidia ? "publisher/model-name" : "model-id"}
              value={customModel} onChange={(e) => setCustomModel(e.target.value)} />
          )}
        </div>

        {p.last_error && !testResult && <p className="form-error">{p.last_error}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
        {testResult && (
          <p className="small" role="status"
            style={{ display: "flex", gap: 8, alignItems: "flex-start", color: testResult.ok ? "var(--positive)" : "var(--negative)" }}>
            {testResult.ok ? <CheckCircle2 size={16} /> : <XCircle size={16} />} <span>{testResult.text}</span>
          </p>
        )}

        <div className="ai-actions">
          {p.source === "settings" && p.needs_key !== false
            ? <button className="btn btn-danger btn-sm" type="button" disabled={Boolean(busy)}
                onClick={() => save({ api_key: "" }, `${p.name} API key removed`)}><Trash2 size={14} /> Remove key</button>
            : <span />}
          <span className="spacer" />
          <button className="btn btn-secondary" type="button" onClick={test} disabled={!p.configured || Boolean(busy)}>
            {busy === "test" ? <span className="spinner" aria-hidden="true" /> : <CheckCircle2 size={15} />} Test
          </button>
          <button className="btn btn-secondary" type="submit" disabled={Boolean(busy)}><Save size={15} /> Save</button>
          {!p.active && (
            <button className="btn" type="button" disabled={Boolean(busy) || (!p.configured && !key.trim())} onClick={() => submit(null, true)}>
              <Zap size={15} /> Save and use
            </button>
          )}
        </div>
      </form>

      <div className="ai-help">
        <span className="eyebrow">Get started</span>
        {STEPS[p.id] ? (
          <ol>{STEPS[p.id].map((step, i) => <li key={i}>{step}</li>)}</ol>
        ) : (
          <ol>
            <li>Create an account with {p.name} and open its API keys page.</li>
            <li>Create a key{p.key_prefix ? <> (it starts with <code>{p.key_prefix}</code>)</> : null}, paste it here and select <b>Save and use</b>.</li>
          </ol>
        )}
        {p.key_url && (
          <a className="btn btn-ghost btn-sm" href={p.key_url} target="_blank" rel="noopener noreferrer">
            {p.id === "ollama" ? "Download Ollama" : `Get a ${p.name} key`} <ExternalLink size={13} />
          </a>
        )}
      </div>
    </Panel>
  );
}

export default function AISettings() {
  const [state, setState] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");

  const apply = useCallback((data) => {
    if (!data) return;
    setState(data);
    setSelected((current) => current || data.active);
  }, []);

  useEffect(() => {
    api("/api/admin/ai").then(apply).catch((err) => setError(err.message));
  }, [apply]);

  if (error && !state) return <p className="form-error">{error}</p>;
  if (!state) return <Loading />;
  const { ai, providers, models } = state;
  const current = providers.find((p) => p.id === selected) || providers[0];
  const active = providers.find((p) => p.id === state.active);

  return (
    <>
      <div className={`ai-banner${ai.available ? " on" : ""}`}>
        <span className="ai-banner-icon"><Cpu size={20} /></span>
        <div>
          <span className="eyebrow">Powering TatvaX now</span>
          <strong>{active?.name}{ai.model ? ` · ${ai.model}` : ""}</strong>
          <span className="small muted">
            {!ai.allowed ? "AI is turned off on the server, so TatvaX answers from the study notes."
              : ai.available ? "Students get AI answers, assessments and translations. If the provider has a problem, TatvaX falls back to the study notes automatically."
                : "Not connected yet, so TatvaX answers from the study notes. Set up a provider below."}
          </span>
        </div>
      </div>

      <div className="provider-grid" role="tablist" aria-label="AI providers">
        {providers.map((p) => {
          const [kind, label] = statusOf(p, ai.allowed);
          return (
            <button key={p.id} type="button" role="tab" aria-selected={p.id === current.id} className={`provider-card${p.active ? " active" : ""}`}
              onClick={() => setSelected(p.id)}>
              <span className="pc-top">
                <strong>{p.name}</strong>
                {FREE.has(p.id) && <span className="pc-free">Free</span>}
              </span>
              <span className="pc-about">{ABOUT[p.id]}</span>
              <span className={`pc-status ${kind}`}><i aria-hidden="true" />{label}</span>
            </button>
          );
        })}
      </div>

      <ProviderPanel key={current.id} provider={current} allowed={ai.allowed} recommended={models} onChanged={apply} />
    </>
  );
}
