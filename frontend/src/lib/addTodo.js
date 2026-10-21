// Create a to-do from elsewhere in the app (assessment results, study notes), linked back to that page.
import { api } from "./api.js";
import { schoolToday } from "./format.js";

export function tomorrow() {
  return schoolToday(1);
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
