// Delete with an "Undo" toast: the item disappears at once, but the server is only asked to
// delete it once the toast has gone. Leaving the page sends any pending deletes straight away.
import { useCallback, useEffect, useRef } from "react";

import { useApp } from "../context/AppContext.jsx";
import { api } from "./api.js";

const UNDO_MS = 6000;

export default function useUndoableDelete({ hide, restore, path }) {
  const { notify } = useApp();
  const pending = useRef(new Map()); // id -> timer

  const commit = useCallback(async (id, item) => {
    pending.current.delete(id);
    try {
      await api(path(id), { method: "DELETE" });
    } catch (err) {
      restore(item);
      notify(err.message, { kind: "error" });
    }
  }, [notify, path, restore]);

  useEffect(() => () => {
    for (const [id, { timer }] of pending.current) {
      clearTimeout(timer);
      api(path(id), { method: "DELETE" }).catch(() => {});
    }
    pending.current.clear();
  }, [path]);

  return useCallback((item, label) => {
    hide(item);
    const timer = setTimeout(() => commit(item.id, item), UNDO_MS);
    pending.current.set(item.id, { timer });
    notify(label, {
      duration: UNDO_MS,
      action: {
        label: "Undo",
        onClick: () => {
          clearTimeout(pending.current.get(item.id)?.timer);
          pending.current.delete(item.id);
          restore(item);
        },
      },
    });
  }, [commit, hide, notify, restore]);
}
