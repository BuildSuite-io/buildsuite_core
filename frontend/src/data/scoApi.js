import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over the buildsuite_core.api.sco.* whitelisted methods (the SCO
// workflow transitions that aren't a single-document save). frappeRequest handles
// the CSRF token + base URL; errors are normalised to Error(<summary>) so callers
// can surface the reason. Mirrors the pattern in usersApi / coreSettingsApi.
async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.sco.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const approveSco = (sco) => call("approve_sco", { sco });
export const rejectSco = (sco, comment) => call("reject_sco", { sco, comment });
export const reviseSco = (sco) => call("revise_sco", { sco });
