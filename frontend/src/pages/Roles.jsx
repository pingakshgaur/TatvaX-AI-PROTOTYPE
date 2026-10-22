// Roles and who holds them, ranked like a Discord server: higher roles outrank lower ones. You can
// only change roles below your own highest role, and only give out permissions you have yourself.
import { ArrowDown, ArrowUp, Crown, Lock, Pencil, Plus, Search, Shield, Trash2, UserCog, Users } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Dialog, EmptyState, Loading, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { api } from "../lib/api.js";

const GROUPS = ["Management", "Teaching", "Learning"];

function RoleChip({ role }) {
  return <span className="role-chip" style={{ "--role": role.color }}><span className="dot" aria-hidden="true" />{role.name}</span>;
}

function RoleEditor({ role, catalog, me, onClose, onSaved }) {
  const { notify } = useApp();
  const creating = !role.id;
  const [name, setName] = useState(role.name || "");
  const [color, setColor] = useState(role.color || "#6366f1");
  const [permissions, setPermissions] = useState(() => new Set(role.permissions || []));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const mine = new Set(me.permissions);

  const toggle = (id) => setPermissions((set) => {
    const next = new Set(set);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });

  const save = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = role.owner ? {} : { name, color, permissions: [...permissions] };
      const data = creating
        ? await api("/api/admin/roles", { method: "POST", body })
        : await api(`/api/admin/roles/${role.id}`, { method: "PATCH", body });
      notify(creating ? `Role created: ${name}` : `Saved ${name}`, { kind: "success" });
      onSaved(data);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <form onSubmit={save} noValidate>
      <div className="role-editor-head">
        <div className="field grow">
          <label className="label" htmlFor="role-name">Role name</label>
          <input className="input" id="role-name" maxLength={40} value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="field">
          <label className="label" htmlFor="role-color">Colour</label>
          <input className="input role-color" id="role-color" type="color" value={color} onChange={(e) => setColor(e.target.value)} />
        </div>
      </div>
      {role.base && <p className="hint">Everyone has this role, guests included. Its permissions are what every learner can do.</p>}
      {GROUPS.map((group) => (
        <fieldset key={group} className="perm-group">
          <legend className="eyebrow">{group}</legend>
          {catalog.filter((p) => p.group === group).map((p) => {
            const locked = !mine.has(p.id);
            return (
              <label key={p.id} className={`perm-row${locked ? " locked" : ""}${p.id === "administrator" ? " danger" : ""}`}>
                <input type="checkbox" checked={permissions.has(p.id)} disabled={locked} onChange={() => toggle(p.id)} />
                <span>
                  <strong>{p.name}</strong>
                  <span className="desc">{p.description}{locked ? " You don't have this permission, so you can't change it." : ""}</span>
                </span>
              </label>
            );
          })}
        </fieldset>
      ))}
      <p className="form-error" role="alert">{error}</p>
      <div className="dialog-footer">
        <button className="btn btn-secondary" type="button" onClick={onClose}>Cancel</button>
        <button className="btn" type="submit" disabled={busy || !name.trim()}>{creating ? "Create role" : "Save role"}</button>
      </div>
    </form>
  );
}

function RoleList({ data, onChange }) {
  const { notify } = useApp();
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const run = async (promise) => {
    try { onChange(await promise); } catch (err) { notify(err.message, { kind: "error" }); }
  };
  const roles = data.roles;

  return (
    <>
      <div className="section-head">
        <h2>Roles</h2>
        <span className="small muted">Higher roles outrank lower ones. You can manage the roles below your own.</span>
        <button className="btn btn-sm" type="button" style={{ marginLeft: "auto" }} onClick={() => setEditing({})}><Plus size={14} /> New role</button>
      </div>
      <Panel tight>
        {roles.map((role, i) => (
          <div key={role.id} className="list-row role-row">
            <span className="role-rank num" aria-label={`Rank ${i + 1}`}>{i + 1}</span>
            <div className="grow">
              <div className="role-title">
                <RoleChip role={role} />
                {role.owner && <span className="tag accent"><Crown size={12} /> Every permission</span>}
                {role.base && <span className="tag">Everyone</span>}
                {!role.editable && !role.owner && <span className="tag" title="This role is level with or above your own"><Lock size={12} /> Above you</span>}
              </div>
              <div className="desc">
                {role.permissions.includes("administrator") && !role.owner ? "Administrator: every permission"
                  : role.owner ? "The school's owner" : `${role.permissions.length} permission${role.permissions.length === 1 ? "" : "s"}`}
                {role.members != null && ` · ${role.members} ${role.members === 1 ? "person" : "people"}`}
              </div>
            </div>
            <div className="role-actions">
              <button className="icon-btn" type="button" aria-label={`Move ${role.name} up`} title="Move up"
                disabled={!role.movable || i <= 1 || !roles[i - 1].movable}
                onClick={() => run(api(`/api/admin/roles/${role.id}/move`, { method: "POST", body: { direction: "up" } }))}><ArrowUp size={15} /></button>
              <button className="icon-btn" type="button" aria-label={`Move ${role.name} down`} title="Move down"
                disabled={!role.movable || i >= roles.length - 2}
                onClick={() => run(api(`/api/admin/roles/${role.id}/move`, { method: "POST", body: { direction: "down" } }))}><ArrowDown size={15} /></button>
              <button className="icon-btn" type="button" aria-label={`Edit ${role.name}`} title="Edit" disabled={!role.editable}
                onClick={() => setEditing(role)}><Pencil size={15} /></button>
              <button className="icon-btn" type="button" aria-label={`Delete ${role.name}`} title="Delete" disabled={!role.deletable}
                onClick={() => setDeleting(role)}><Trash2 size={15} /></button>
            </div>
          </div>
        ))}
      </Panel>

      <Dialog open={Boolean(editing)} wide onClose={() => setEditing(null)} title={editing?.id ? `Edit ${editing.name}` : "New role"}>
        {editing && <RoleEditor role={editing} catalog={data.permissions} me={data.me} onClose={() => setEditing(null)}
          onSaved={(next) => { setEditing(null); onChange(next); }} />}
      </Dialog>
      <Dialog open={Boolean(deleting)} onClose={() => setDeleting(null)} title="Delete role">
        <p>Delete <strong>{deleting?.name}</strong>? {deleting?.members ? `${deleting.members} ${deleting.members === 1 ? "person loses" : "people lose"} its permissions.` : ""}</p>
        <div className="dialog-footer">
          <button className="btn btn-secondary" type="button" onClick={() => setDeleting(null)}>Cancel</button>
          <button className="btn btn-danger" type="button" onClick={() => {
            const id = deleting.id;
            setDeleting(null);
            run(api(`/api/admin/roles/${id}`, { method: "DELETE" }));
          }}><Trash2 size={15} /> Delete</button>
        </div>
      </Dialog>
    </>
  );
}

function MemberRoles({ person, data, onClose, onSaved }) {
  const [chosen, setChosen] = useState(() => new Set(person.roles));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const save = async () => {
    setBusy(true);
    try {
      onSaved(await api(`/api/admin/members/${person.id}/roles`, { method: "PUT", body: { role_ids: [...chosen] } }));
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };
  return (
    <>
      <p className="small muted">Everyone also has the base role. You can give or take away roles below your own.</p>
      {data.roles.filter((r) => !r.owner && !r.base).map((role) => (
        <label key={role.id} className={`perm-row${role.assignable ? "" : " locked"}`}>
          <input type="checkbox" checked={chosen.has(role.id)} disabled={!role.assignable}
            onChange={() => setChosen((set) => { const next = new Set(set); if (next.has(role.id)) next.delete(role.id); else next.add(role.id); return next; })} />
          <span><RoleChip role={role} />{!role.assignable && <span className="desc"> Level with or above your own role</span>}</span>
        </label>
      ))}
      <p className="form-error" role="alert">{error}</p>
      <div className="dialog-footer">
        <button className="btn btn-secondary" type="button" onClick={onClose}>Cancel</button>
        <button className="btn" type="button" disabled={busy} onClick={save}>Save roles</button>
      </div>
    </>
  );
}

function TransferOwnership({ person, onClose, onDone }) {
  const { notify, refreshUser } = useApp();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault();
    try {
      const data = await api("/api/admin/owner/transfer", { method: "POST", body: { user_id: person.id, password } });
      notify(`${person.name} is now the Owner. You keep the Admin role.`, { kind: "success" });
      await refreshUser();
      onDone(data);
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <form onSubmit={submit}>
      <p>Make <strong>{person.name}</strong> the Owner? They will have every permission, and you will no longer be able to
        take ownership back yourself. You keep the Admin role if it still exists.</p>
      <div className="field">
        <label className="label" htmlFor="owner-password">Your password, to confirm</label>
        <input className="input" id="owner-password" type="password" autoComplete="current-password" value={password}
          onChange={(e) => setPassword(e.target.value)} required />
      </div>
      <p className="form-error" role="alert">{error}</p>
      <div className="dialog-footer">
        <button className="btn btn-secondary" type="button" onClick={onClose}>Cancel</button>
        <button className="btn btn-danger" type="submit" disabled={!password}><Crown size={15} /> Transfer ownership</button>
      </div>
    </form>
  );
}

function People({ data, onChange }) {
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState(null);
  const [transferring, setTransferring] = useState(null);
  const byId = useMemo(() => Object.fromEntries(data.roles.map((r) => [r.id, r])), [data.roles]);
  const shown = data.members.filter((m) => !query.trim()
    || `${m.name} ${m.email || ""}`.toLowerCase().includes(query.trim().toLowerCase()));

  return (
    <>
      <div className="section-head">
        <h2>People</h2>
        <label className="history-search" style={{ marginLeft: "auto" }}>
          <Search size={15} aria-hidden="true" />
          <span className="sr-only">Search people</span>
          <input type="search" placeholder="Search by name or email" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
      </div>
      {shown.length === 0 ? <Panel><EmptyState icon={Users} title="Nobody found" /></Panel> : (
        <Panel tight>
          {shown.map((m) => (
            <div key={m.id} className="list-row">
              <div className="grow">
                <strong>{m.name}</strong>{m.is_me && <span className="small muted"> (you)</span>}
                <div className="desc">{m.email}{m.grade ? ` · Class ${m.grade}` : ""}</div>
                <div className="role-chips">
                  {m.is_owner && <span className="role-chip owner"><Crown size={12} /> Owner</span>}
                  {m.roles.map((id) => byId[id]).filter((r) => r && !r.owner).map((r) => <RoleChip key={r.id} role={r} />)}
                  {!m.is_owner && !m.roles.length && <span className="small muted">Base role only</span>}
                </div>
              </div>
              <div className="role-actions">
                <button className="btn btn-sm btn-secondary" type="button" disabled={!m.manageable || m.is_owner}
                  title={m.manageable ? "Change roles" : "Ranked level with or above you"} onClick={() => setEditing(m)}>
                  <UserCog size={14} /> Roles
                </button>
                {data.me.is_owner && !m.is_me && (
                  <button className="btn btn-sm btn-ghost" type="button" onClick={() => setTransferring(m)} title="Make this person the Owner">
                    <Crown size={14} /> Make owner
                  </button>
                )}
              </div>
            </div>
          ))}
        </Panel>
      )}
      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} title={`Roles for ${editing?.name || ""}`}>
        {editing && <MemberRoles person={editing} data={data} onClose={() => setEditing(null)}
          onSaved={(next) => { setEditing(null); onChange(next); }} />}
      </Dialog>
      <Dialog open={Boolean(transferring)} onClose={() => setTransferring(null)} title="Transfer ownership">
        {transferring && <TransferOwnership person={transferring} onClose={() => setTransferring(null)}
          onDone={(next) => { setTransferring(null); onChange(next); }} />}
      </Dialog>
    </>
  );
}

export default function Roles() {
  const { refreshUser } = useApp();
  const [view, setView] = useState("roles");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api("/api/admin/members").then(setData).catch((err) => setError(err.message));
  }, []);
  useEffect(() => { load(); }, [load]);

  // Role changes can change what the person looking may do, so refresh them too. Role edits return
  // only the roles, so reload the people list alongside.
  const onChange = (next) => {
    if (next.members) setData(next);
    else load();
    refreshUser();
  };

  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <Loading />;
  return (
    <>
      <div className="segmented" role="group" aria-label="Show" style={{ marginBottom: 16 }}>
        <button type="button" aria-pressed={view === "roles"} onClick={() => setView("roles")}><Shield size={14} /> Roles</button>
        <button type="button" aria-pressed={view === "people"} onClick={() => setView("people")}><Users size={14} /> People</button>
      </div>
      {view === "roles" ? <RoleList data={data} onChange={onChange} /> : <People data={data} onChange={onChange} />}
    </>
  );
}
