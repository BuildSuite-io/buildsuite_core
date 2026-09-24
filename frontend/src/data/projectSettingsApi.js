import { frappeRequest } from "frappe-ui-frappe-request";

import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.project_settings.* — the two-level Project page-tab
// visibility (site-wide template + sparse per-project override).

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.project_settings.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// The site-wide tab template: { tabs: { tabId: shown } } (any signed-in user).
export const getProjectSettings = () => call("get_project_settings");

// Replace the template (admin only). `tabs` = { tabId: shown }.
export const setProjectSettings = (tabs) =>
	call("set_project_settings", { tabs: JSON.stringify(tabs || {}) });

// A project's sparse overrides: { tabId: shown } for tabs it explicitly Shows/Hides.
export const getProjectTabOverrides = (project) => call("get_project_tab_overrides", { project });

// Replace a project's overrides (requires Project write). `overrides` = { tabId: bool }, explicit
// Show/Hide only (Default omitted).
export const setProjectTabOverrides = (project, overrides) =>
	call("set_project_tab_overrides", { project, overrides: JSON.stringify(overrides || {}) });
