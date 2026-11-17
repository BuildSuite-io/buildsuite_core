// The day petty cash was paid out ("Paid on"): the date the disbursement Journal Entry is
// posted on, chosen by whoever disburses or issues it. Today by default, never a day still to
// come, never before the request. The server applies the same rule
// (utils.petty_cash.disbursement_date_for); this one answers in the form, before posting.
import { fmtDate } from "./format";
import { __ } from "./translate";

// Today in the user's own timezone. toISOString() is UTC, which east of Greenwich is still
// yesterday in the early morning, so a "today" picked then would read as a day in the future.
export function localToday(now = new Date()) {
	return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

// What is wrong with a Paid on date, or "" when nothing is.
export function disbursementDateIssue(date, { requestDate = "", today = localToday() } = {}) {
	if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(Date.parse(date)))
		return __("Pick the date the cash was paid.");
	if (date > today) return __("The date cannot be in the future.");
	if (requestDate && date < String(requestDate).slice(0, 10))
		return __("The cash cannot be paid before it was requested, on {0}.", [
			fmtDate(requestDate),
		]);
	return "";
}

// The day a disbursed record was paid. Records from before Paid on existed fall back to when the
// disbursement was recorded, then to the request date.
export function paidOnOf(row) {
	if (!row || row.status !== "Disbursed") return "";
	return (
		row.disbursement_date ||
		(row.disbursed_on ? String(row.disbursed_on).slice(0, 10) : "") ||
		row.request_date ||
		""
	);
}
