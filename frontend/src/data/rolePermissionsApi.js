import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.role_permissions.* — the admin actions for the
// BuildSuite default role-permission matrix (restore the shipped defaults; export the site's
// current DocPerms for hand-back). Admin only, enforced server-side.

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.role_permissions.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// Re-apply BuildSuite's shipped default DocPerm matrix (overwrites in-Desk customizations).
export const restoreDefaultRolePermissions = () => call("restore_default_role_permissions");

// The site's current BuildSuite-role DocPerms, grouped by doctype (JSON snapshot to hand back).
export const exportRolePermissions = () => call("export_role_permissions");
