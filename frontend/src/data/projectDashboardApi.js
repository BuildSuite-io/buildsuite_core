import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Site Execution › Project Dashboard — one aggregate read, scoped to the whole portfolio
// or a single project (buildsuite_core.api.project_dashboard.get_project_dashboard).
export async function getProjectDashboard(project) {
	try {
		return await frappeRequest({
			url: "buildsuite_core.api.project_dashboard.get_project_dashboard",
			params: project ? { project } : {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Failed to load the dashboard.");
	}
}
