import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";
import { costCodeToFields } from "@/utils/costCode";

// Thin wrapper over buildsuite_core.api.field_attendance — a day's attendance
// sheet for one project. The save goes through here because its `employee_list`
// child table can't go through the generic adapter. List reads use the adapter.

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.field_attendance.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getFieldAttendance = (name) => call("get_field_attendance", { name });

// The form holds cost codes as CostCodePicker objects; the server takes the flat fields.
export const saveFieldAttendance = ({ cost_code, ...payload }) =>
	call("save_field_attendance", {
		...payload,
		...costCodeToFields(cost_code),
		employee_list: JSON.stringify(
			(payload.employee_list || []).map(({ cost_code: rowCode, ...row }) => ({
				...row,
				...costCodeToFields(rowCode),
			}))
		),
	});

// These refuse while a workflow governs Field Attendance — its transitions take over.
export const submitFieldAttendance = (name) => call("submit_field_attendance", { name });
export const cancelFieldAttendance = (name) => call("cancel_field_attendance", { name });
export const amendFieldAttendance = (name) => call("amend_field_attendance", { name });

// Workers allocated to the project.
export const getRoster = (project) => call("get_roster", { project });
