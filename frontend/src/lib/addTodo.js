// Create a to-do from elsewhere in the app (assessment results, study notes), linked back to that page.
import { api } from "./api.js";

export function tomorrow() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export default async function addTodo(notify, navigate, todo) {
  try {
    const { todo: saved } = await api("/api/todos", { method: "POST", body: todo });
    notify(`Added to your to-do list: ${saved.title}`, {
      kind: "success", duration: 5000, action: { label: "Open list", onClick: () => navigate("/todos") },
    });
  } catch (err) {
    notify(err.message, { kind: "error" });
  }
}
