import { frappeRequest } from "frappe-ui-frappe-request";

import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.todo.* — the user's personal to-do list (Frappe ToDo).

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

export const listMyTodos = () => call("list_my_todos");
export const myOpenTodoCount = () => call("my_open_todo_count");
export const saveTodo = (payload) => call("save_todo", payload || {});
export const setTodoStatus = (name, status) => call("set_todo_status", { name, status });
export const deleteTodo = (name) => call("delete_todo", { name });
