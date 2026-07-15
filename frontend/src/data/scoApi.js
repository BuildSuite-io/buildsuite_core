import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.sco.* — the Scope Change Order approval
// transitions (approve / reject / revise) and the BOQ-revision tie-in. Plain CRUD
// goes through the generic data adapter.

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

export const approveSco = (name) => call("approve_sco", { name });
export const rejectSco = (name, reason) => call("reject_sco", { name, reason });
export const reviseSco = (name) => call("revise_sco", { name });
export const createBoqRevision = (name) => call("create_boq_revision", { name });
