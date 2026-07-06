// Thin wrappers over buildsuite_core.api.project_template.* — read/write the
// ERPNext Project Template behind a Project Category (its default Work Packages,
// Stages and Tasks). POST with the CSRF token; throws Error(<server message>).

const BASE = "/api/method/buildsuite_core.api.project_template.";

function serverMessage(payload, status) {
	try {
		const sm = payload?._server_messages;
		if (sm) {
			const first = JSON.parse(JSON.parse(sm)[0]);
			if (first?.message) return first.message;
		}
	} catch (_) {
		/* fall through */
	}
	return payload?.exception || `Request failed (${status})`;
}

async function request(method, body) {
	const res = await fetch(BASE + method, {
		method: "POST",
		credentials: "include",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			"X-Frappe-CSRF-Token": window.csrf_token || "",
		},
		body: JSON.stringify(body || {}),
	});
	const payload = await res.json().catch(() => ({}));
	if (!res.ok) throw new Error(serverMessage(payload, res.status));
	return payload.message;
}

export const getProjectTemplate = (projectCategory) =>
	request("get_project_template", { project_category: projectCategory });

export const saveProjectTemplate = (projectCategory, { workPackages, stages, tasks }) =>
	request("save_project_template", {
		project_category: projectCategory,
		work_packages: JSON.stringify(workPackages || []),
		stages: JSON.stringify(stages || []),
		tasks: JSON.stringify(tasks || []),
	});
