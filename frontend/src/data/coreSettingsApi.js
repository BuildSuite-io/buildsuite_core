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
// Petty Cash Account — the configurable Cash/Bank float petty cash and expenses post to/from.
export const setPettyCashAccount = (account) => call("set_petty_cash_account", { account });
export const setProjectNaming = (projectNaming) =>
	call("set_project_naming", { project_naming: projectNaming });
// Naming mode + series options for the New Project form (available to any user).
export const getProjectNaming = () => call("get_project_naming");
