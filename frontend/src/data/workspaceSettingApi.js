import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.workspace_setting.* — the per-workspace
// report-style shortcut tiles (Workspace Setting Single).

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.workspace_setting.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// Ordered, renderable report tiles for a workspace (any signed-in user).
export const getWorkspaceReports = (workspace) => call("get_workspace_reports", { workspace });

// Admin config for the settings screen: { workspaces: [{slug,label}], reports: {slug:[…]} }.
export const getWorkspaceSettings = () => call("get_workspace_settings");

// Replace one workspace's rows (order preserved). Admin only.
export const setWorkspaceReports = (workspace, reports) =>
	call("set_workspace_reports", { workspace, reports: JSON.stringify(reports || []) });
