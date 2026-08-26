import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Cost vs Budget by Cost Code — planned / committed / actual / variance per BOQ cost code for a
// project, grouped by cost type. Backed by buildsuite_core.api.cost_report. Returns flat rows;
// the view groups + filters client-side.
export async function getCostVsBudget(project) {
	try {
		return await frappeRequest({
			url: "buildsuite_core.api.cost_report.cost_vs_budget_by_cost_code",
			params: { project: project || "" },
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Failed to load Cost vs Budget.");
	}
}
