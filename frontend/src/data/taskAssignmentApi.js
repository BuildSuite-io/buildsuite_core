// Thin wrappers around the buildsuite_core.api.task_assignment whitelisted
// methods. Mirrors data/projectTeamApi.js. Assignee is Frappe-native `_assign`
// (single-assignee semantics enforced server-side).
import { serverErrorMessage } from "@/utils/frappeError";

function serverMessage(data, status) {
	const message = serverErrorMessage(data?._server_messages);
	if (message) return message;
	return data?.exception || data?.exc_type || `Request failed (${status})`;
}

async function call(method, args) {
	const res = await fetch(`/api/method/buildsuite_core.api.task_assignment.${method}`, {
		method: "POST",
		credentials: "include",
		headers: {
			"Content-Type": "application/json",
			"X-Frappe-CSRF-Token": window.csrf_token || "",
		},
		body: JSON.stringify(args || {}),
	});
	const data = await res.json().catch(() => ({}));
	if (!res.ok) throw new Error(serverMessage(data, res.status));
	return data.message;
}

export const setTaskAssignee = (task, assignee) =>
	call("set_task_assignee", { task, assignee: assignee || "" });
export const getTaskAssignee = (task) => call("get_task_assignee", { task });
