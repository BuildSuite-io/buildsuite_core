import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.site_execution.* — the Site Execution
// workspace reports (Site Execution Settings Single).

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.site_execution.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// Ordered reports for the workspace (any signed-in user).
export const getSiteExecutionReports = () => call("get_site_execution_reports");
// Admin config for the settings screen.
export const getSiteExecutionSettings = () => call("get_site_execution_settings");
export const setSiteExecutionReports = (reports) =>
	call("set_site_execution_reports", { reports: JSON.stringify(reports || []) });
