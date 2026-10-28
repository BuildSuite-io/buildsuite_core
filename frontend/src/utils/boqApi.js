// Thin wrappers over the buildsuite_core.api.boq.* whitelisted methods (the BOQ
// operations that aren't a single-document save). POST with the CSRF token; throws
// Error(<server message>) so callers can surface the reason.

const BASE = "/api/method/buildsuite_core.api.boq.";

function serverMessage(payload, status) {
	try {
		const sm = payload?._server_messages;
		if (sm) {
			const first = JSON.parse(JSON.parse(sm)[0]);
			if (first?.message) return first.message;
		}
	} catch (_) {
		/* fall through */
	}
	return payload?.exception || `Request failed (${status})`;
}

async function request(method, body) {
	const res = await fetch(BASE + method, {
		method: "POST",
		credentials: "include",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			"X-Frappe-CSRF-Token": window.csrf_token || "",
		},
		body: JSON.stringify(body || {}),
	});
	const payload = await res.json().catch(() => ({}));
	if (!res.ok) throw new Error(serverMessage(payload, res.status));
	return payload.message;
}

// --- BOQ actuals log (buildsuite_core.api.boq_actuals.*) — the cost-code actuals
// that feed the Actual column + the per-code drill-down. Same request shape, different module.
const ACTUALS_BASE = "/api/method/buildsuite_core.api.boq_actuals.";
async function requestActuals(method, body) {
	const res = await fetch(ACTUALS_BASE + method, {
		method: "POST",
		credentials: "include",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			"X-Frappe-CSRF-Token": window.csrf_token || "",
		},
		body: JSON.stringify(body || {}),
	});
	const payload = await res.json().catch(() => ({}));
	if (!res.ok) throw new Error(serverMessage(payload, res.status));
	return payload.message;
}
export const getActualsSummary = (project) => requestActuals("get_actuals_summary", { project });
export const getActualsForCode = (project, groupCode = null, itemCode = null) =>
	requestActuals("get_actuals_for_code", {
		project,
		group_code: groupCode,
		item_code: itemCode,
	});
export const getActualsLog = (project, filters = {}) =>
	requestActuals("get_actuals_log", { project, ...filters });
// {project: total} for many projects in one call — the BOQ list's Actual column, same cost-code
// calculation path as getActualsSummary so a row reconciles with the BOQ page.
export const getActualsTotals = (projects) =>
	requestActuals("get_actuals_totals", { projects: JSON.stringify(projects || []) });

export const submitBoq = (boq) => request("submit_boq", { boq });
export const approveBoq = (boq) => request("approve_boq", { boq });
export const explodeItem = (boqItem) => request("explode_item", { boq_item: boqItem });
export const createRevision = (boq, sourceSco = null, title = null) =>
	request("create_revision", { boq, source_sco: sourceSco, title });
export const cloneBoq = (payload) => request("clone_boq", payload);
export const importTemplate = (boq, estimateTemplate) =>
	request("import_template", { boq, estimate_template: estimateTemplate });
// Create groups + items on a Draft BOQ from a parsed spreadsheet import (buildPayload output).
// Returns { boq, items, groups }.
export const importBoqRows = (boq, payload) =>
	request("import_rows", { boq, payload: JSON.stringify(payload) });

// Raise a bid from an Approved BOQ. kind = "Quotation" | "Tender"; lineMode = "item" | "group".
// Returns { doctype, name } so the caller can route to the new document.
export const createBidFromBoq = (
	boq,
	kind,
	lineMode = "item",
	title = null,
	submissionDeadline = null
) =>
	request("create_bid_from_boq", {
		boq,
		kind,
		line_mode: lineMode,
		title,
		submission_deadline: submissionDeadline,
	});

// Attach a project-less estimate (and its whole revision lineage) to a project once the work is
// won. Returns { moved, project }.
export const attachEstimateToProject = (boq, project) =>
	request("attach_estimate_to_project", { boq, project });

// Create a Project from an Approved, project-less BOQ — maps BOQ groups to Work Packages and
// (unless work is "packages"/"none") items to Tasks. Returns { project, project_name, work }.
export const createProjectFromBoq = (boq, data = {}) =>
	request("create_project_from_boq", {
		boq,
		name: data.name ?? null,
		code: data.code ?? null,
		project_category: data.projectCategory ?? null,
		project_type: data.projectType ?? null,
		start_date: data.startDate ?? null,
		end_date: data.endDate ?? null,
		pm: data.pm ?? null,
		work: data.work ?? "tasks",
		group_ids: JSON.stringify(data.groupIds ?? null),
	});

// Create Work Packages + Tasks from an Approved BOQ already attached to a project. Idempotent.
// Returns { work_packages, tasks }.
export const setUpWorkFromBoq = (boq, data = {}) =>
	request("set_up_work_from_boq", {
		boq,
		work: data.work ?? "tasks",
		group_ids: JSON.stringify(data.groupIds ?? null),
	});

// The BOQ's groups with amount / item count / existing-WP / tasks-to-create — drives the
// "create project" modal checklist. Returns { groups, total, has_project }.
export const boqWorkPlan = (boq) => request("boq_work_plan", { boq });

// The bid (if any) a project would be created from — its kind, name and priced total. Returns
// { kind, doctype, name, taxable } or null. Drives the "Create project" primary action.
export const boqWonOffer = (boq) => request("boq_won_offer", { boq });
