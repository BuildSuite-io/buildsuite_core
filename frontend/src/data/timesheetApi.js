import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.timesheet — timesheets on the native Timesheet doctype:
// one worker, one day, rows of hours against a project and cost code.

async function call(method, params) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.timesheet.${method}`,
			params: params || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getTimesheet = (name) => call("get_timesheet", { name });

// { employee_name, trade, daily_rate, overtime_rate, full_day_hours, hourly_rate, project_name }:
// what the form shows under the header ("an hour (daily rate ÷ h, the full day on Block A)").
export const getCostingInfo = (employee, project, date) =>
	call("costing_info", { employee, project: project || "", date: date || "" });

// payload: { employee, date, note, rows: [{ project, cost_code, hours, is_overtime, description }],
//            name?, submit? } -> the saved timesheet.
export const saveTimesheet = ({ rows, ...rest }) =>
	call("save_timesheet", {
		...rest,
		time_logs: JSON.stringify(rows),
		submit: rest.submit ? 1 : 0,
	});

export const submitTimesheet = (name) => call("submit_timesheet", { name });
export const cancelTimesheet = (name) => call("cancel_timesheet", { name });

// The workbook to fill in. A chosen date and cost code are filled on every row; a chosen project
// lists its workers and its estimate's cost codes.
export function timesheetTemplateUrl({ project = "", costCode = null, date = "" } = {}) {
	const q = new URLSearchParams();
	if (project) q.set("project", project);
	if (project && costCode) q.set("cost_code", JSON.stringify(costCode));
	if (date) q.set("date", date);
	const s = q.toString();
	return `/api/method/buildsuite_core.api.timesheet.timesheet_template${s ? `?${s}` : ""}`;
}

async function post(method, body) {
	const res = await fetch(`/api/method/buildsuite_core.api.timesheet.${method}`, {
		method: "POST",
		credentials: "include",
		headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
		body,
	});
	const json = await res.json().catch(() => ({}));
	if (!res.ok) {
		let msg = "Request failed.";
		try {
			if (json._server_messages)
				msg = JSON.parse(JSON.parse(json._server_messages)[0]).message;
		} catch {
			/* keep default */
		}
		throw new Error(msg);
	}
	return json.message;
}

// Read an uploaded .xlsx / .csv and say what it would create (nothing is saved):
// { groups, skipped, blank, legacy_task, header_found }.
export function previewTimesheetImport(file) {
	const fd = new FormData();
	fd.append("file", file, file.name);
	return post("preview_import", fd);
}

// Create one timesheet per previewed group: { created: [names], failed: [{ key, reason }] }.
export function createTimesheets(groups, submit = false) {
	const fd = new FormData();
	fd.append("groups", JSON.stringify(groups));
	fd.append("submit", submit ? "1" : "0");
	return post("create_timesheets", fd);
}
