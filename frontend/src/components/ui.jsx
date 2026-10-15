import { X } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";

import { useApp } from "../context/AppContext.jsx";
import { renderInline, renderMarkdown } from "../lib/markdown.js";

export function Markdown({ source, className = "prose", ...rest }) {
  const html = useMemo(() => renderMarkdown(source), [source]);
  return <div className={className} dir="auto" dangerouslySetInnerHTML={{ __html: html }} {...rest} />;
}

export function InlineMarkdown({ source }) {
  const html = useMemo(() => renderInline(source), [source]);
  return <span dir="auto" dangerouslySetInnerHTML={{ __html: html }} />;
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
  const { toasts } = useApp();
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast ${toast.kind}`}>
          <div>
            <span className="toast-title">{toast.title}</span>
            {toast.detail && <span className="toast-detail">{toast.detail}</span>}
          </div>
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
