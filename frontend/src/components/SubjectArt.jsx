// Original flat illustrations that give every subject the same visual identity across TatvaX:
// as a small logo tile and as the large backdrop on subject cards. Colours come from the
// subject's own colour (--tone), so teacher-added subjects get a matching generic design.

function Maths() {
  return (
    <>
      <circle className="tl" cx="84" cy="34" r="22" />
      <path className="t" d="M18 96 L58 30 L98 96 Z" />
      <path className="w" d="M58 50 L78 88 L38 88 Z" opacity="0.92" />
      <rect className="ink" x="14" y="100" width="92" height="8" rx="3" />
      {[24, 36, 48, 60, 72, 84, 96].map((x) => <rect key={x} className="w" x={x} y="100" width="2" height="4" />)}
      <text className="w" x="84" y="42" textAnchor="middle" fontSize="22" fontWeight="700" fontFamily="Georgia, serif">π</text>
      <path className="ink line" d="M22 22 h12 M28 16 v12" strokeWidth="4" strokeLinecap="round" />
    </>
  );
}

function Science() {
  return (
    <>
      <ellipse className="tl line" cx="60" cy="60" rx="48" ry="18" transform="rotate(-28 60 60)" strokeWidth="4" />
      <path className="t" d="M48 14 h24 v26 l24 50 a8 8 0 0 1 -7 12 H31 a8 8 0 0 1 -7 -12 l24 -50 Z" />
      <path className="w" d="M33 82 Q60 72 87 82 l4 9 a5 5 0 0 1 -4 7 H33 a5 5 0 0 1 -4 -7 Z" opacity="0.95" />
      <rect className="ink" x="44" y="10" width="32" height="8" rx="4" />
      <circle className="w" cx="52" cy="62" r="4" />
      <circle className="w" cx="66" cy="52" r="3" />
      <circle className="w" cx="60" cy="38" r="2.5" />
      <circle className="tl" cx="98" cy="28" r="7" />
    </>
  );
}

function English() {
  return (
    <>
      <circle className="tl" cx="90" cy="28" r="16" />
      <path className="t" d="M12 30 Q36 22 60 34 V100 Q36 88 12 96 Z" />
      <path className="ink" d="M108 30 Q84 22 60 34 V100 Q84 88 108 96 Z" />
      <path className="w line" d="M20 44 Q36 39 52 46 M20 56 Q36 51 52 58 M20 68 Q36 63 52 70" strokeWidth="3" strokeLinecap="round" opacity="0.9" />
      <text className="w" x="84" y="74" textAnchor="middle" fontSize="28" fontWeight="700" fontFamily="Georgia, serif">Aa</text>
      <text className="ink" x="90" y="35" textAnchor="middle" fontSize="20" fontWeight="700" fontFamily="Georgia, serif">“</text>
    </>
  );
}

function Social() {
  return (
    <>
      <circle className="t" cx="56" cy="62" r="40" />
      <path className="w" d="M30 46 q10 -6 18 2 q6 8 -4 14 q-8 6 -2 14 q4 8 -6 10 q-8 -10 -10 -24 Z M66 30 q14 2 22 14 q-8 4 -14 0 q-6 -4 -8 -14 Z M72 66 q10 -2 16 6 q-2 12 -14 16 q-6 -10 -2 -22 Z" opacity="0.93" />
      <ellipse className="ink line" cx="56" cy="62" rx="40" ry="14" strokeWidth="2.5" opacity="0.55" />
      <path className="ink line" d="M56 22 v80" strokeWidth="2.5" opacity="0.55" />
      <path className="tl" d="M96 14 a12 12 0 0 1 12 12 c0 10 -12 22 -12 22 s-12 -12 -12 -22 a12 12 0 0 1 12 -12 Z" />
      <circle className="w" cx="96" cy="26" r="4.5" />
    </>
  );
}

function Companion() {
  return (
    <>
      <path className="t" d="M14 24 a10 10 0 0 1 10 -10 h56 a10 10 0 0 1 10 10 v36 a10 10 0 0 1 -10 10 H44 l-16 14 v-14 h-4 a10 10 0 0 1 -10 -10 Z" />
      <circle className="w" cx="34" cy="42" r="5" /><circle className="w" cx="52" cy="42" r="5" /><circle className="w" cx="70" cy="42" r="5" />
      <path className="ink" d="M62 78 l20 -12 l20 12 v28 H62 Z" />
      <rect className="w" x="77" y="88" width="10" height="18" rx="2" />
      <path className="tl" d="M100 22 l3 7 l7 3 l-7 3 l-3 7 l-3 -7 l-7 -3 l7 -3 Z" />
    </>
  );
}

function All() {
  return (
    <>
      <rect className="t" x="14" y="14" width="42" height="42" rx="12" />
      <circle className="ink" cx="85" cy="35" r="21" />
      <path className="tl" d="M35 66 l22 40 H13 Z" />
      <rect className="t" x="64" y="64" width="42" height="42" rx="21" opacity="0.7" />
      <path className="w line" d="M28 35 h14 M35 28 v14" strokeWidth="4" strokeLinecap="round" />
      <path className="w line" d="M78 28 l14 14 M92 28 l-14 14" strokeWidth="4" strokeLinecap="round" />
    </>
  );
}

function Generic() {
  return (
    <>
      <circle className="tl" cx="88" cy="30" r="18" />
      <rect className="t" x="18" y="74" width="74" height="16" rx="4" />
      <rect className="ink" x="26" y="56" width="68" height="16" rx="4" />
      <rect className="t" x="22" y="38" width="62" height="16" rx="4" opacity="0.75" />
      <rect className="w" x="28" y="80" width="40" height="4" rx="2" />
      <rect className="w" x="34" y="62" width="34" height="4" rx="2" opacity="0.8" />
      <path className="ink line" d="M14 96 h92" strokeWidth="4" strokeLinecap="round" />
    </>
  );
}

const ART = { maths: Maths, science: Science, english: English, social: Social, companion: Companion, all: All, generic: Generic };

export function artFor(subject) {
  if (!subject || subject === "all") return "all";
  const key = `${subject.slug || ""} ${subject.title || ""}`.toLowerCase();
  if (subject.kind === "helpdesk" || subject.slug === "school-faq" || subject === "tatvai") return "companion";
  if (/math|algebra|geometry|ganit/.test(key)) return "maths";
  if (/science|physics|chemistry|biology/.test(key)) return "science";
  if (/english|language|grammar|literature/.test(key)) return "english";
  if (/social|history|geography|civics|economics/.test(key)) return "social";
  return "generic";
}

export function toneFor(subject) {
  if (!subject || subject === "all") return "var(--c-indigo)";
  if (subject === "tatvai") return "var(--c-plum)";
  return subject.color || "var(--c-teal)";
}

// variant "logo": a small rounded tile; "backdrop": the bare illustration for card backgrounds.
export default function SubjectArt({ subject, variant = "logo", size = 44, className = "" }) {
  const Art = ART[artFor(subject)];
  const tone = toneFor(subject);
  if (variant === "backdrop") {
    return (
      <svg className={`subject-art backdrop ${className}`} viewBox="0 0 120 120" aria-hidden="true" style={{ "--tone": tone }}>
        <Art />
      </svg>
    );
  }
  return (
    <span className={`subject-logo ${className}`} style={{ "--tone": tone, width: size, height: size }} aria-hidden="true">
      <svg className="subject-art" viewBox="0 0 120 120"><Art /></svg>
    </span>
  );
}
