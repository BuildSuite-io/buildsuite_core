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

// --- DocType shortcut tiles (the generic /records list + form) ---

// Ordered, renderable DocType tiles for a workspace (any signed-in user).
export const getWorkspaceDoctypes = (workspace) => call("get_workspace_doctypes", { workspace });

// Replace one workspace's DocType rows (order preserved). Admin only.
export const setWorkspaceDoctypes = (workspace, doctypes) =>
	call("set_workspace_doctypes", { workspace, doctypes: JSON.stringify(doctypes || []) });

// DocTypeListView props derived from a DocType's Frappe meta (allow-listed only).
export const getDoctypeListConfig = (doctype) => call("get_doctype_list_config", { doctype });

// The current user's action permissions on a DocType, for gating New / Save / Delete.
export const getDoctypePermissions = (doctype) => call("get_doctype_permissions", { doctype });
