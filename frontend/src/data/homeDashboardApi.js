import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Home / Desk overview — one aggregate read backing AppHomeView (/home) and DashboardView
// (/dashboard): app-wide KPIs, active projects, pending SCOs and in-progress tasks
// (buildsuite_core.api.home.get_home_dashboard).
export async function getHomeDashboard() {
	try {
		return await frappeRequest({
			url: "buildsuite_core.api.home.get_home_dashboard",
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Failed to load the dashboard.");
	}
}
