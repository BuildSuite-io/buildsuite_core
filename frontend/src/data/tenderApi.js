import { frappeRequest } from "frappe-ui-frappe-request";

import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.tender.* — a tender's lifecycle (Draft -> Submitted ->
// Under Evaluation -> Awarded / Rejected), copying one to re-price, and the list's figures.

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.tender.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const TENDER_STATUSES = ["Draft", "Submitted", "Under Evaluation", "Awarded", "Rejected"];

export const setTenderStatus = (name, status) => call("set_tender_status", { name, status });
// { name } of the new draft copy
export const copyTender = (name) => call("copy_tender", { name });
// { total, due_soon: [{ name, title, submission_deadline, overdue }], in_play, emd_at_stake,
//   awarded_value, win_rate (null when nothing is decided) }
export const getTenderKpis = () => call("tender_kpis");
