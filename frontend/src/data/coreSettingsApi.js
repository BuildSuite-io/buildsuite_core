import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.core_settings.* — the server-persisted
// BuildSuite Core Settings (Single doctype). Admin only.

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.core_settings.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getCoreSettings = () => call("get_core_settings");
export const setProjectNaming = (projectNaming, projectNamingSeries) =>
	call("set_project_naming", {
		project_naming: projectNaming,
		project_naming_series: projectNamingSeries || "",
	});
