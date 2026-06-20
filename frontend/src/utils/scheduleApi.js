// Thin wrappers over the buildsuite_core.api.schedule.* whitelisted methods.
// Used by the Task Detail "Dependencies" section and (later) the Gantt. Reads are
// GET; mutations are POST with the CSRF token. Throws Error(<server message>) so
// callers can surface the cycle-guard message etc.

const BASE = "/api/method/buildsuite_core.api.schedule.";

function serverMessage(payload, status) {
	// Frappe puts thrown messages in _server_messages: a JSON array of JSON strings.
	try {
		const sm = payload?._server_messages;
		if (sm) {
			const first = JSON.parse(JSON.parse(sm)[0]);
			if (first?.message) return first.message;
		}
	} catch (_) {
		/* fall through to generic */
	}
	return payload?.exception || `Request failed (${status})`;
}

async function request(method, { params, body } = {}) {
	const qs = params ? "?" + new URLSearchParams(params).toString() : "";
	const res = await fetch(BASE + method + qs, {
		method: body ? "POST" : "GET",
		credentials: "include",
		headers: {
			Accept: "application/json",
			...(body
				? {
						"Content-Type": "application/json",
						"X-Frappe-CSRF-Token": window.csrf_token || "",
				  }
				: {}),
		},
		...(body ? { body: JSON.stringify(body) } : {}),
	});
	const payload = await res.json().catch(() => ({}));
	if (!res.ok) throw new Error(serverMessage(payload, res.status));
	return payload.message;
}

export const getProjectSchedule = (project) =>
	request("get_project_schedule", { params: { project } });

export const getTaskDependencies = (task) =>
	request("get_task_dependencies", { params: { task } });

export const addTaskPredecessor = (task, predecessor, dependency_type = "FS", lag_days = 0) =>
	request("add_task_predecessor", { body: { task, predecessor, dependency_type, lag_days } });

export const removeTaskPredecessor = (task, predecessor) =>
	request("remove_task_predecessor", { body: { task, predecessor } });
