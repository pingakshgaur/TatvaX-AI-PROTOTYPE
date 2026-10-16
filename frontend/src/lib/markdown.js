// Sanitised Markdown with KaTeX maths.
import DOMPurify from "dompurify";
import katex from "katex";
import "katex/dist/katex.min.css";
import { marked } from "marked";

marked.setOptions({ breaks: true, gfm: true });

const MATH_PATTERNS = [
  [/\$\$([\s\S]+?)\$\$/g, true],
  [/\\\[([\s\S]+?)\\\]/g, true],
  [/\\\(([\s\S]+?)\\\)/g, false],
  // Inline $...$, but not currency such as "$5".
  [/(?<![\\$\w])\$(?!\s)([^\n$]+?)(?<!\s)\$(?![\w$])/g, false],
];

const escapeHtml = (value) =>
  String(value).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);

export function renderMarkdown(source) {
  const maths = [];
  let text = String(source ?? "");
  for (const [pattern, display] of MATH_PATTERNS) {
    text = text.replace(pattern, (_match, tex) => {
      maths.push({ tex, display });
      return `@@MATH${maths.length - 1}@@`;
    });
  }
  const html = DOMPurify.sanitize(marked.parse(text));
  // KaTeX output is generated and escaped by KaTeX itself, after sanitising.
  return html.replace(/@@MATH(\d+)@@/g, (_match, index) => {
    const { tex, display } = maths[Number(index)];
    try {
      return katex.renderToString(tex, { displayMode: display, throwOnError: false, trust: false });
    } catch {
      return escapeHtml(tex);
    }
  });
}

// For short snippets (quiz options): Markdown without the wrapping paragraph.
export function renderInline(source) {
  return renderMarkdown(source).trim().replace(/^<p>([\s\S]*)<\/p>$/, "$1");
}

export function plainText(markdown) {
  const div = document.createElement("div");
  div.innerHTML = renderMarkdown(markdown);
  div.querySelectorAll(".katex-mathml").forEach((el) => el.remove());
  return div.textContent.trim();
}
