// Full-screen celebration for achievements, level-ups and completed daily goals:
// a medal reveal, a confetti burst and a short chime, queued one after another.
import { Sparkles, Target } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useApp } from "../context/AppContext.jsx";
import { BadgeIcon } from "../lib/badgeIcons.jsx";

const GLOW = {
  common: "#16b3a0",
  rare: "#4a8dff",
  epic: "#c062e6",
  legendary: "#f5b21f",
  level: "#f5b21f",
  goal: "#4cc95e",
};
const CONFETTI = ["#0e9f8e", "#f2a516", "#ef5f4a", "#4f63e0", "#3fa34d", "#a548c7", "#ffffff"];
const PARTICLES = { common: 90, rare: 130, epic: 170, legendary: 230, level: 220, goal: 150 };
const reducedMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

function playChime(tier) {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    // A rising arpeggio; rarer rewards get a longer, brighter run.
    const scale = { common: [523, 659, 784], rare: [523, 659, 784, 1047], epic: [523, 659, 784, 1047, 1319],
      legendary: [392, 523, 659, 784, 1047, 1319, 1568], level: [392, 523, 659, 784, 1047, 1319, 1568], goal: [523, 659, 784, 1047] };
    const notes = scale[tier] || scale.common;
    const now = ctx.currentTime;
    notes.forEach((freq, i) => {
      const start = now + i * 0.085;
      for (const [type, detune, volume] of [["triangle", 0, 0.16], ["sine", 1200, 0.05]]) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = type;
        osc.frequency.value = freq;
        osc.detune.value = detune;
        gain.gain.setValueAtTime(0, start);
        gain.gain.linearRampToValueAtTime(volume, start + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.9);
        osc.connect(gain).connect(ctx.destination);
        osc.start(start);
        osc.stop(start + 1);
      }
    });
    setTimeout(() => ctx.close(), 2500);
  } catch {
    /* audio is optional */
  }
}

function useConfetti(canvasRef, tier, active) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !active || reducedMotion()) return undefined;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const resize = () => {
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    const originY = h * 0.38;
    const count = PARTICLES[tier] || 120;
    const particles = Array.from({ length: count }, (_, i) => {
      const angle = (Math.PI * 2 * i) / count + Math.random() * 0.4;
      const speed = 5 + Math.random() * 9;
      return {
        x: w / 2, y: originY,
        vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed - 4,
        size: 5 + Math.random() * 7, rot: Math.random() * Math.PI, vr: (Math.random() - 0.5) * 0.35,
        color: CONFETTI[i % CONFETTI.length], shape: i % 3, life: 0,
      };
    });
    let frame;
    const start = performance.now();
    const tick = (time) => {
      const elapsed = (time - start) / 1000;
      ctx.clearRect(0, 0, w, h);
      for (const p of particles) {
        p.vy += 0.22;
        p.vx *= 0.985;
        p.vy *= 0.985;
        p.x += p.vx;
        p.y += p.vy;
        p.rot += p.vr;
        ctx.save();
        ctx.globalAlpha = Math.max(0, 1 - elapsed / 3.2);
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.fillStyle = p.color;
        if (p.shape === 0) ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
        else if (p.shape === 1) { ctx.beginPath(); ctx.arc(0, 0, p.size / 2.6, 0, Math.PI * 2); ctx.fill(); }
        else { ctx.beginPath(); ctx.moveTo(0, -p.size / 2); ctx.lineTo(p.size / 2, p.size / 2); ctx.lineTo(-p.size / 2, p.size / 2); ctx.fill(); }
        ctx.restore();
      }
      if (elapsed < 3.4) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [canvasRef, tier, active]);
}

function CountUp({ to, duration = 900 }) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (reducedMotion()) { setValue(to); return undefined; }
    let frame;
    const start = performance.now();
    const step = (time) => {
      const t = Math.min(1, (time - start) / duration);
      setValue(Math.round(to * (1 - (1 - t) ** 3)));
      if (t < 1) frame = requestAnimationFrame(step);
    };
    const delay = setTimeout(() => { frame = requestAnimationFrame(step); }, 550);
    return () => { clearTimeout(delay); cancelAnimationFrame(frame); };
  }, [to, duration]);
  return value;
}

export default function Celebration() {
  const { celebrations, dismissCelebration, sound, xpPop } = useApp();
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const buttonRef = useRef(null);
  const current = celebrations[0];
  const tier = current?.type === "badge" ? current.badge.rarity : current?.type;

  useConfetti(canvasRef, tier, Boolean(current));

  useEffect(() => {
    if (!current) return undefined;
    if (sound) playChime(tier);
    buttonRef.current?.focus();
    const onKey = (event) => { if (event.key === "Escape") dismissCelebration(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [current, sound, tier, dismissCelebration]);

  const pop = xpPop && <div className="xp-pop" key={xpPop.id} aria-hidden="true"><Sparkles size={14} /> +{xpPop.amount} XP</div>;
  if (!current) return pop || null;

  let eyebrow, title, body, medal, xp = null;
  if (current.type === "badge") {
    eyebrow = `${current.badge.rarity} achievement unlocked`;
    title = current.badge.name;
    body = current.badge.description;
    medal = <BadgeIcon name={current.badge.icon} size={46} />;
  } else if (current.type === "level") {
    eyebrow = "Level up";
    title = `You reached level ${current.level}`;
    body = "Your hard work is paying off. New challenges await.";
    medal = <span className="level-number">{current.level}</span>;
  } else {
    eyebrow = "Daily goal complete";
    title = "Goal smashed!";
    body = `${current.goal.done} learning activities today. Come back tomorrow to keep your streak going.`;
    medal = <Target size={46} strokeWidth={1.75} aria-hidden="true" />;
    xp = current.goal.bonus_xp;
  }

  return (
    <>
      {pop}
      <div className="celebrate" role="dialog" aria-modal="true" aria-label={`${eyebrow}: ${title}`}
        style={{ "--glow": GLOW[tier] || GLOW.common }}
        onClick={(event) => { if (event.target === event.currentTarget) dismissCelebration(); }}>
        <canvas ref={canvasRef} aria-hidden="true" />
        <div className="celebrate-card" key={current.id}>
          <div className="celebrate-rays" aria-hidden="true" />
          <div className="medal">{medal}</div>
          <span className="celebrate-eyebrow">{eyebrow}</span>
          <h2>{title}</h2>
          <p>{body}</p>
          {xp ? <div className="celebrate-xp">+<CountUp to={xp} /><small>XP</small></div> : <div style={{ height: 18 }} />}
          <div className="celebrate-actions">
            <button ref={buttonRef} className="btn btn-lg" type="button" onClick={dismissCelebration}>
              {celebrations.length > 1 ? "Next" : "Keep going"}
            </button>
            {current.type === "badge" && (
              <button className="btn btn-lg btn-ghost" type="button"
                onClick={() => { dismissCelebration(); navigate("/progress#achievements"); }}>View achievements</button>
            )}
          </div>
          {celebrations.length > 1 && <div className="celebrate-count">{celebrations.length - 1} more reward{celebrations.length > 2 ? "s" : ""} waiting</div>}
        </div>
      </div>
    </>
  );
}
