import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrapper over buildsuite_core.api.field_employee.save_field_employee — a
// Field Employee is an ERPNext Employee with `is_labour` set. The save goes
// through here because its `custom_project_assigned` child table can't go
// through the generic adapter. Read and delete still use the adapter.

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.field_employee.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const saveFieldEmployee = (payload) =>
	call("save_field_employee", {
		...payload,
		allocated_projects: JSON.stringify(payload.allocated_projects || []),
	});
