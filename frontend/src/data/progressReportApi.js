import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Project Progress Report (S167) — one windowed aggregate read
// (buildsuite_core.api.progress_report.get_progress_report). period = daily|weekly|monthly,
// ending on `date` (today if omitted); scoped to the project + its sub-projects.
export async function getProgressReport(project, period = "weekly", date) {
	try {
		return await frappeRequest({
			url: "buildsuite_core.api.progress_report.get_progress_report",
			params: { project, period, ...(date ? { date } : {}) },
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Failed to load the progress report.");
	}
}
