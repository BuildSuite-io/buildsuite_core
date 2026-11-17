import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Workforce dashboard figures — buildsuite_core.api.workforce.get_dashboard:
// { active_workers, active_crews, man_days, labour_cost, recent_attendance, recent_labour }.
export async function getWorkforceDashboard() {
	try {
		return await frappeRequest({ url: "buildsuite_core.api.workforce.get_dashboard" });
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// Labour Cost Summary — buildsuite_core.api.labour_cost_summary.get_summary. `group_by` is
// "project" | "code" | "worker"; `source` is "" | "Attendance" | "Timesheet".
export async function getLabourCostSummary(params) {
	try {
		return await frappeRequest({
			url: "buildsuite_core.api.labour_cost_summary.get_summary",
			params,
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}
