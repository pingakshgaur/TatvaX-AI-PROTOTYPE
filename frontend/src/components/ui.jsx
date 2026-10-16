import { X } from "lucide-react";
import { lazy, Suspense, useEffect, useRef, useState } from "react";

import { useApp } from "../context/AppContext.jsx";

// The Markdown and maths renderer is a large download, so it loads the first time it is needed;
// until then the text is shown as it is.
const loadView = () => import("./MarkdownView.jsx");
const MarkdownBlock = lazy(() => loadView().then((m) => ({ default: m.MarkdownBlock })));
const MarkdownInline = lazy(() => loadView().then((m) => ({ default: m.MarkdownInline })));

export function Markdown({ source, className = "prose", ...rest }) {
  return (
    <Suspense fallback={<div className={className} dir="auto" style={{ whiteSpace: "pre-wrap" }} {...rest}>{source}</div>}>
      <MarkdownBlock source={source} className={className} {...rest} />
    </Suspense>
  );
}

export function InlineMarkdown({ source }) {
  return <Suspense fallback={<span dir="auto">{source}</span>}><MarkdownInline source={source} /></Suspense>;
}

export function Loading({ label = "Loading" }) {
  return (
    <div className="loading" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="empty-state">
      {Icon && <Icon className="empty-icon" size={28} strokeWidth={1.5} aria-hidden="true" />}
      {title && <h2>{title}</h2>}
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function PageHeader({ eyebrow, title, lede, actions }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {lede && <p className="lede">{lede}</p>}
      </div>
      {actions && <div className="actions">{actions}</div>}
    </header>
  );
}

export function Panel({ title, actions, children, tight = false, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      {(title || actions) && (
        <div className="panel-header">
          {typeof title === "string" ? <h2>{title}</h2> : title}
          {actions}
        </div>
      )}
      <div className={`panel-body${tight ? " tight" : ""}`}>{children}</div>
    </section>
  );
}

export function Dialog({ open, onClose, title, wide = false, children }) {
  const ref = useRef(null);
  const { t } = useApp();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={`dialog${wide ? " wide" : ""}`}
      aria-label={title}
      onClose={onClose}
      onClick={(event) => { if (event.target === ref.current) onClose(); }}
    >
      {open && (
        <>
          <div className="dialog-header">
            <h2>{title}</h2>
            <button className="icon-btn" type="button" onClick={onClose} aria-label={t("close")}><X size={18} /></button>
          </div>
          <div className="dialog-body">{children}</div>
        </>
      )}
    </dialog>
  );
}

export function Toasts() {
  const { toasts, dismissToast } = useApp();
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast ${toast.kind}`}>
          <div style={{ flex: 1 }}>
            <span className="toast-title">{toast.title}</span>
            {toast.detail && <span className="toast-detail">{toast.detail}</span>}
          </div>
          {toast.action && (
            <button type="button" className="toast-action" onClick={() => { dismissToast(toast.id); toast.action.onClick(); }}>
              {toast.action.label}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

export function Meter({ value, label }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="meter" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label={label}>
      <span style={{ width: `${pct}%` }} />
    </div>
  );
}

// Animates a number from its previous value to the new one.
export function CountUp({ value, duration = 900 }) {
  const [shown, setShown] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    const target = Number(value) || 0;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) { setShown(target); from.current = target; return undefined; }
    let frame;
    const start = performance.now();
    const begin = from.current;
    const step = (time) => {
      const t = Math.min(1, (time - start) / duration);
      const next = Math.round(begin + (target - begin) * (1 - (1 - t) ** 3));
      setShown(next);
      if (t < 1) frame = requestAnimationFrame(step);
      else from.current = target;
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [value, duration]);
  return <>{new Intl.NumberFormat().format(shown)}</>;
}
