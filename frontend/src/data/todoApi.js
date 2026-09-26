import { frappeRequest } from "frappe-ui-frappe-request";

import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.todo.* — the user's to-dos (Frappe ToDo).

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.todo.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// { me, can_see_all, todos: [...] } — the current user's visible to-dos, enriched with names + refs
// + a `read` flag (Frappe `_seen`).
export const listTodos = () => call("list_todos");
// Unread to-dos allocated to me — the top-nav badge.
export const myUnreadTodoCount = () => call("my_unread_todo_count");
// Mark a to-do read (its `_seen`) — called when it's opened.
export const markTodoRead = (name) => call("mark_todo_read", { name });
export const saveTodo = (payload) => call("save_todo", payload || {});
export const setTodoStatus = (name, status) => call("set_todo_status", { name, status });
export const deleteTodo = (name) => call("delete_todo", { name });
