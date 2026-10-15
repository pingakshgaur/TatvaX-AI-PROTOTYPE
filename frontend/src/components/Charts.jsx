// Single-series SVG charts: thin bars with rounded data ends, a hairline grid, a tooltip on
// hover and keyboard focus, and a screen-reader table carrying the same values.
import { useEffect, useRef, useState } from "react";

import { formatNumber } from "../lib/format.js";

function useWidth(fallback = 600) {
  const ref = useRef(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const update = () => setWidth(Math.max(260, Math.round(el.clientWidth)));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

function niceMax(value) {
  if (value <= 4) return 4;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 2.5, 5, 10].find((s) => s * magnitude * 4 >= value) * magnitude;
  return step * 4;
}

// Rounded data end, square at the baseline.
function barPath(x, y, w, h, horizontal) {
  if (w <= 0 || h <= 0) return "";
  const r = Math.min(3, horizontal ? h / 2 : w / 2, horizontal ? w : h);
  if (horizontal) return `M${x},${y} h${w - r} a${r},${r} 0 0 1 ${r},${r} v${h - 2 * r} a${r},${r} 0 0 1 ${-r},${r} h${-(w - r)} z`;
  return `M${x},${y + h} v${-(h - r)} a${r},${r} 0 0 1 ${r},${-r} h${w - 2 * r} a${r},${r} 0 0 1 ${r},${r} v${h - r} z`;
}

function DataTable({ items, caption, valueName }) {
  return (
    <table className="sr-only">
      <caption>{caption}</caption>
      <thead><tr><th>Label</th><th>{valueName}</th></tr></thead>
      <tbody>{items.map((d) => <tr key={d.label}><td>{d.title || d.label}</td><td>{d.display ?? d.value}</td></tr>)}</tbody>
    </table>
  );
}

function useTooltip() {
  const [tip, setTip] = useState(null);
  const show = (event, text) => {
    const box = event.currentTarget.ownerSVGElement.parentElement.getBoundingClientRect();
    const bar = event.currentTarget.getBoundingClientRect();
    setTip({ text, x: bar.left - box.left + bar.width / 2, y: bar.top - box.top });
  };
  const node = tip && <div className="chart-tooltip" style={{ left: tip.x, top: tip.y }} aria-hidden="true">{tip.text}</div>;
  return { show, hide: () => setTip(null), node };
}

export function ColumnChart({ items, caption, valueName = "Value", height = 210 }) {
  const [ref, width] = useWidth();
  const { show, hide, node } = useTooltip();
  const pad = { top: 18, right: 4, bottom: 26, left: 34 };
  const max = niceMax(Math.max(1, ...items.map((d) => d.value)));
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const band = innerW / Math.max(items.length, 1);
  const barW = Math.min(22, band - 2);
  const every = Math.ceil(52 / band);
  const y = (v) => pad.top + innerH - (v / max) * innerH;
  const peak = items.reduce((best, d, i) => (d.value > items[best].value ? i : best), 0);

  return (
    <div className="chart" ref={ref}>
      <svg width={width} height={height} role="group" aria-label={caption}>
        <g className="axis">
          {[0.25, 0.5, 0.75, 1].map((f) => (
            <g key={f}>
              <line className="grid-line" x1={pad.left} x2={width - pad.right} y1={y(max * f)} y2={y(max * f)} />
              <text x={pad.left - 8} y={y(max * f) + 4} textAnchor="end">{formatNumber(max * f)}</text>
            </g>
          ))}
          <line className="baseline" x1={pad.left} x2={width - pad.right} y1={y(0)} y2={y(0)} />
          <text x={pad.left - 8} y={y(0) + 4} textAnchor="end">0</text>
        </g>
        {items.map((d, i) => {
          const x = pad.left + i * band + (band - barW) / 2;
          const text = `${d.title || d.label}: ${d.display ?? formatNumber(d.value)}`;
          return (
            <g className="bar-group" key={d.label + i}>
              <path className="bar" d={barPath(x, y(d.value), barW, (d.value / max) * innerH, false)} />
              {i === peak && d.value > 0 && (
                <text className="value-label" x={x + barW / 2} y={y(d.value) - 6} textAnchor="middle">{formatNumber(d.value)}</text>
              )}
              {i % every === 0 && (
                <g className="axis"><text x={x + barW / 2} y={height - 8} textAnchor="middle">{d.label}</text></g>
              )}
              <rect className="bar-hit" x={pad.left + i * band} y={pad.top} width={band} height={innerH}
                tabIndex={0} role="img" aria-label={text}
                onPointerEnter={(e) => show(e, text)} onPointerLeave={hide} onFocus={(e) => show(e, text)} onBlur={hide} />
            </g>
          );
        })}
      </svg>
      {node}
      <DataTable items={items} caption={caption} valueName={valueName} />
    </div>
  );
}

export function BarList({ items, caption, valueName = "Value", max: fixedMax }) {
  const [ref, width] = useWidth();
  const { show, hide, node } = useTooltip();
  const row = 34;
  const labelW = Math.min(180, Math.round(width * 0.36));
  const valueW = 70;
  const height = items.length * row;
  const max = fixedMax ?? Math.max(1, ...items.map((d) => d.value));
  const innerW = width - labelW - valueW;
  const maxChars = Math.floor(labelW / 7.4);

  return (
    <div className="chart" ref={ref}>
      <svg width={width} height={height} role="group" aria-label={caption}>
        {items.map((d, i) => {
          const top = i * row + 6;
          const w = Math.max(d.value > 0 ? 3 : 0, (d.value / max) * innerW);
          const text = `${d.title || d.label}: ${d.display ?? formatNumber(d.value)}`;
          const label = d.label.length > maxChars ? `${d.label.slice(0, maxChars - 1)}…` : d.label;
          return (
            <g className="bar-group" key={d.label + i}>
              <text className="cat-label" x={0} y={top + 14}>{label}</text>
              <path className="bar" d={barPath(labelW, top + 2, w, 16, true)} />
              <text className="value-label" x={labelW + w + 8} y={top + 14}>{d.display ?? formatNumber(d.value)}</text>
              <rect className="bar-hit" x={0} y={top - 2} width={width} height={row - 4} tabIndex={0} role="img" aria-label={text}
                onPointerEnter={(e) => show(e, text)} onPointerLeave={hide} onFocus={(e) => show(e, text)} onBlur={hide} />
            </g>
          );
        })}
      </svg>
      {node}
      <DataTable items={items} caption={caption} valueName={valueName} />
    </div>
  );
}

export function Ring({ fraction, size = 104, stroke = 8, label, sub }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - Math.max(0, Math.min(1, fraction)));
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`${label} ${sub || ""}`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--primary-tint)" strokeWidth={stroke} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--primary)" strokeWidth={stroke}
        strokeDasharray={c} strokeDashoffset={offset} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      <text className="ring-label" x="50%" y={sub ? "46%" : "50%"} textAnchor="middle" dominantBaseline="middle"
        fill="var(--ink)" fontSize={size / 4.2} fontWeight="600">{label}</text>
      {sub && <text className="ring-label" x="50%" y="67%" textAnchor="middle" fill="var(--ink-3)" fontSize={size / 10}>{sub}</text>}
    </svg>
  );
}
