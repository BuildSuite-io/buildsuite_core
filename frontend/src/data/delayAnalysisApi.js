import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Delay Analysis report data — stages (slip + downstream), silent tasks and the weekly
// completion trend for a project. Backed by buildsuite_core.api.delay_analysis.
export async function getDelayAnalysis(project) {
	try {
		return await frappeRequest({
			url: "buildsuite_core.api.delay_analysis.delay_analysis",
			params: { project: project || "" },
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Failed to load Delay Analysis.");
	}
}
