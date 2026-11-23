// Thin wrappers around the buildsuite_core.api.project_team whitelisted methods.
// Mirrors data/usersApi.js.
import { serverErrorMessage } from "@/utils/frappeError";

function serverMessage(data, status) {
	const message = serverErrorMessage(data?._server_messages);
	if (message) return message;
	return data?.exception || data?.exc_type || `Request failed (${status})`;
}

async function call(method, args) {
	const res = await fetch(`/api/method/buildsuite_core.api.project_team.${method}`, {
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

export const addProjectTeamMember = (project, user) =>
	call("add_project_team_member", { project, user });
export const removeProjectTeamMember = (project, user) =>
	call("remove_project_team_member", { project, user });
