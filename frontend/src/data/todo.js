// The to-do vocabulary — a 1:1 mirror of Frappe's ToDo doctype, with one deliberate extension
// ('In Progress') so the board is three columns, not two. Ported from the prototype (S365).

/** Every status a to-do can hold; order is the workflow order. */
export const TODO_STATUSES = ["Open", "In Progress", "Closed", "Cancelled"];

/** The board's columns — Cancelled is NOT one (it's a decision to stop, not a stage). */
export const TODO_BOARD_STATUSES = ["Open", "In Progress", "Closed"];

/** A to-do in one of these is finished as far as "what's on my plate" goes. */
export const TODO_DONE_STATUSES = ["Closed", "Cancelled"];

export const TODO_PRIORITIES = ["High", "Medium", "Low"];

// reference_type -> icon + the in-app route back to the record. The label comes from the backend
// (reference_label), so this only maps presentation.
const REF_DEFS = [
	{ type: "Project", icon: "clipboard-list", route: (id) => `/projects/${id}` },
	{ type: "Task", icon: "check-circle", route: (id) => `/tasks/${id}` },
	{ type: "Work Package", icon: "layout-grid", route: (id) => `/work-packages/${id}` },
	{ type: "Stage Planning", icon: "calendar", route: (id) => `/stage-plannings/${id}` },
	{ type: "BOQ", icon: "estimation", route: (id) => `/boq/${id}` },
	{ type: "Scope Change Order", icon: "file-text", route: (id) => `/sco/${id}` },
];

/** The record a to-do is about, resolved for display — or null. */
export function todoReference(todo) {
	if (!todo?.reference_type || !todo?.reference_name) return null;
	const def = REF_DEFS.find((r) => r.type === todo.reference_type);
	return {
		type: todo.reference_type,
		name: todo.reference_name,
		icon: def?.icon || "file-text",
		to: def ? def.route(todo.reference_name) : null,
		label: todo.reference_label || todo.reference_name,
	};
}

/** The heading for a card or a list row — the first line of the description, trimmed. */
export function todoTitle(todo, max = 90) {
	const first = String(todo?.description || "").split("\n")[0].trim();
	if (!first) return "(no description)";
	return first.length > max ? first.slice(0, max - 1).trimEnd() + "…" : first;
}

/** Whatever is left of the description once the title has taken its first line. */
export function todoBody(todo) {
	return String(todo?.description || "").split("\n").slice(1).join("\n").trim();
}

/** Due-date urgency — null for an undated or already-finished to-do (a badge there is noise). */
export function todoDue(todo, todayISO) {
	if (!todo?.date || TODO_DONE_STATUSES.includes(todo.status)) return null;
	const days = Math.round(
		(new Date(todo.date + "T00:00:00") - new Date(todayISO + "T00:00:00")) / 86400000
	);
	if (days < 0) return { days, tone: "overdue", text: days === -1 ? "Yesterday" : `${-days}d overdue` };
	if (days === 0) return { days, tone: "today", text: "Today" };
	if (days === 1) return { days, tone: "soon", text: "Tomorrow" };
	if (days <= 7) return { days, tone: "soon", text: `In ${days}d` };
	return { days, tone: "later", text: null };
}
