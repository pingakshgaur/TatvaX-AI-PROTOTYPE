// Demo mode only (python run.py --demo): a bar of demo accounts to switch between in one click,
// and for the account in use, a list of the features worth showing.
import { ChevronDown, Presentation } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";

const TOUR_KEY = "tatvax-demo-tour"; // session storage: whether the tour list is open

function readTourOpen() {
  try { return sessionStorage.getItem(TOUR_KEY) !== "closed"; } catch { return true; }
}

export default function DemoBar() {
  const { user, notify } = useApp();
  const [data, setData] = useState(null);
  const [switching, setSwitching] = useState(null);
  const [tourOpen, setTourOpen] = useState(readTourOpen);

  useEffect(() => {
    api("/api/demo").then(setData).catch(() => setData(null));
  }, [user?.id]);

  useEffect(() => {
    try { sessionStorage.setItem(TOUR_KEY, tourOpen ? "open" : "closed"); } catch { /* unavailable */ }
  }, [tourOpen]);

  if (!data) return null;
  const active = data.personas.find((p) => p.active) || (user && !user.is_guest ? null : data.personas.find((p) => p.key === "guest"));

  const switchTo = async (persona) => {
    if (persona.key === active?.key) { setTourOpen(true); return; }
    setSwitching(persona.key);
    try {
      const { start } = await api("/api/demo/switch", { method: "POST", body: { persona: persona.key } });
      window.location.assign(start); // a fresh start, so every page shows the new account
    } catch (err) {
      notify(err.message, { kind: "error" });
      setSwitching(null);
    }
  };

  return (
    <div className="demo-wrap">
      <div className="demo-bar" role="region" aria-label="Demo accounts">
        <span className="demo-label" title={data.school}><Presentation size={15} aria-hidden="true" /> Demo</span>
        <div className="demo-personas" role="group" aria-label="View TatvaX as">
          {data.personas.map((p) => (
            <button key={p.key} type="button" aria-pressed={p.key === active?.key} disabled={switching != null}
              title={`${p.name}: ${p.summary}`} onClick={() => switchTo(p)}>
              <span className="demo-avatar" aria-hidden="true">{switching === p.key ? <span className="spinner" /> : p.initials}</span>
              <span className="demo-who"><b>{p.label}</b><small>{p.role}</small></span>
            </button>
          ))}
        </div>
        {active && (
          <button className="demo-tour-toggle" type="button" aria-expanded={tourOpen} onClick={() => setTourOpen((v) => !v)}>
            What to show <ChevronDown size={14} aria-hidden="true" />
          </button>
        )}
      </div>
      {active && tourOpen && (
        <nav className="demo-tour" aria-label={`Features to show as ${active.label}`}>
          <p><strong>{active.name}</strong> · {active.summary}</p>
          <ol>
            {active.tour.map(([label, path]) => (
              <li key={path + label}>
                {path.startsWith("/print/")
                  ? <a href={path} target="_blank" rel="noopener">{label}</a>
                  : <Link to={path}>{label}</Link>}
              </li>
            ))}
          </ol>
        </nav>
      )}
    </div>
  );
}
