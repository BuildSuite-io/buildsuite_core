// What the SPA calls a quotation, derived from ERPNext's own fields. `status` is never rewritten:
// ERPNext reaches "Ordered" only through a Sales Order and its daily job turns an offer past its
// validity into "Expired". "Accepted" is `accepted_on`. This is the same table as
// buildsuite_core/utils/quotation.py (OFFER_STATUS_FILTERS); keep them together.

export const OFFER_STATUSES = ["Draft", "Sent", "Accepted", "Rejected", "Expired", "Cancelled"];

// Label -> ERPNext filters. Each is a plain AND, so a list filter and a label cannot disagree.
export const OFFER_STATUS_FILTERS = {
	Draft: [["docstatus", "=", 0]],
	Sent: [
		["docstatus", "=", 1],
		["status", "in", ["Open", "Replied"]],
		["accepted_on", "is", "not set"],
	],
	Accepted: [
		["docstatus", "=", 1],
		["status", "!=", "Lost"],
		["accepted_on", "is", "set"],
	],
	Rejected: [
		["docstatus", "=", 1],
		["status", "=", "Lost"],
	],
	Expired: [
		["docstatus", "=", 1],
		["status", "=", "Expired"],
		["accepted_on", "is", "not set"],
	],
	Cancelled: [["docstatus", "=", 2]],
};

/** The label for a quotation row/doc: needs docstatus, status and accepted_on. */
export function offerStatus(q) {
	if (!q) return "";
	if (q.docstatus === 0) return "Draft";
	if (q.docstatus === 2) return "Cancelled";
	if (q.status === "Lost") return "Rejected";
	if (q.accepted_on) return "Accepted";
	if (q.status === "Expired") return "Expired";
	return "Sent";
}
