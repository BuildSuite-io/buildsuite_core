// Thin wrapper over the buildsuite_core.utils.project template methods — the category-template
// preview and the post-creation import (⋯ menu → Import project template).
function serverMessage(data, status) {
	if (data?._server_messages) {
		try {
			const first = JSON.parse(data._server_messages)[0];
			const parsed = JSON.parse(first);
			if (parsed?.message) return String(parsed.message).replace(/<[^>]*>/g, "");
		} catch {
			/* fall through */
		}
	}
	return data?.exception || data?.exc_type || `Request failed (${status})`;
}

async function call(method, args) {
	const res = await fetch(`/api/method/buildsuite_core.utils.project.${method}`, {
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

// Preview of a category's template: { exists, stage_names, stage_count, work_package_count, task_count }.
export const getProjectTemplateSummary = (projectCategory) =>
	call("get_project_template_summary", { project_category: projectCategory });

// Import the category template into an existing project, appending the chosen layers (existing
// data is kept). `opts` = { workPackages, stages, tasks } booleans. Returns counts created.
export const importProjectTemplate = (project, { workPackages, stages, tasks } = {}) =>
	call("import_project_template", {
		project,
		work_packages: workPackages ? 1 : 0,
		stages: stages ? 1 : 0,
		tasks: tasks ? 1 : 0,
	});
