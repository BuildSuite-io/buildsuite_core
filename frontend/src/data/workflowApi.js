import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Generic Frappe-Workflow bridge (buildsuite_core.api.workflow.*). Lets any detail view
// ask whether an active workflow governs its doctype and, if so, drive the transitions
// the signed-in user may take. When no workflow is configured, `active` is false and the
// caller keeps its plain docstatus (Submit / Cancel) buttons.
async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.workflow.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// name is optional — omit it to just probe whether the doctype has an active workflow.
export const getWorkflowInfo = (doctype, name) => call("get_workflow_info", { doctype, name });
export const applyWorkflowAction = (doctype, name, action) =>
	call("apply_action", { doctype, name, action });
