// Markdown and KaTeX rendering, loaded on first use (see Markdown in ui.jsx).
import { useMemo } from "react";

import { renderInline, renderMarkdown } from "../lib/markdown.js";

export function MarkdownBlock({ source, className, ...rest }) {
  const html = useMemo(() => renderMarkdown(source), [source]);
  return <div className={className} dir="auto" dangerouslySetInnerHTML={{ __html: html }} {...rest} />;
}

export function MarkdownInline({ source }) {
  const html = useMemo(() => renderInline(source), [source]);
  return <span dir="auto" dangerouslySetInnerHTML={{ __html: html }} />;
}
