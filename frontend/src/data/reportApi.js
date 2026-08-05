import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Runs a Frappe/ERPNext Report (Query or Script) and returns its columns + rows for the
// generic FrappeReport renderer (buildsuite_core.api.report.run_report).
async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.report.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const runReport = (report, filters) =>
	call("run_report", { report, filters: filters ? JSON.stringify(filters) : undefined });

// The report's own filter definitions (Report Filter child table) for the filter bar.
export const getReportFilters = (report) => call("get_report_filters", { report });
