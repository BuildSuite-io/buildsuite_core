// Sales › Leads — the vocabulary the board, the lead page and the quotation form share. Field
// names are ERPNext Lead's own (Source is `utm_source` in v16). The rules themselves are enforced
// by the backend (buildsuite_core.utils.lead); these mirror them so the UI only offers what saves.

// Board columns, in order. Do Not Contact has no column: stopping is a decision, not a stage.
export const LEAD_BOARD_STATUSES = [
	"Lead",
	"Open",
	"Interested",
	"Quotation",
	"Lost Quotation",
	"Converted",
];
export const LEAD_STATUSES = [...LEAD_BOARD_STATUSES, "Do Not Contact"];
// Set by hand. Quotation / Lost Quotation follow the lead's quotations; Converted, its customer.
export const LEAD_MANUAL_STATUSES = ["Lead", "Open", "Interested"];
export const LEAD_SYSTEM_STATUSES = ["Quotation", "Lost Quotation", "Converted"];
export const DO_NOT_CONTACT = "Do Not Contact";

// The statuses a lead's own page can offer. A converted lead's is fixed; one with quotations
// follows them (Do Not Contact still can be set, and taking it back hands it to them again).
export function leadStatusOptions(lead) {
	if (!lead) return [];
	if (lead.status === "Converted" || lead.customer) return ["Converted"];
	if (lead.quotation_count) {
		const opts = [lead.status, DO_NOT_CONTACT];
		if (lead.status === DO_NOT_CONTACT) opts.push("Open");
		return [...new Set(opts)];
	}
	return [...LEAD_MANUAL_STATUSES, DO_NOT_CONTACT];
}

export function leadStatusHint(lead) {
	if (!lead) return "";
	if (lead.status === "Converted" || lead.customer) return "A customer now.";
	if (lead.quotation_count) return "Follows its quotations. Do Not Contact still can be set.";
	return "Lead → Open → Interested by hand; a quotation moves it on.";
}

// The last ten digits, so +91 98471 20101, 098471-20101 and 9847120101 are one person.
export function mobileKey(mobile) {
	const digits = String(mobile || "").replace(/\D/g, "");
	return digits.length >= 10 ? digits.slice(-10) : "";
}

// Search a lead by name, organisation, mobile (typed with or without spaces), email, place or id.
export function leadMatchesSearch(lead, query) {
	const q = String(query || "")
		.trim()
		.toLowerCase();
	if (!q) return true;
	const hay = [
		lead.lead_name,
		lead.company_name,
		lead.mobile_no,
		lead.email_id,
		lead.city,
		lead.name,
	]
		.filter(Boolean)
		.join(" ")
		.toLowerCase();
	if (hay.includes(q)) return true;
	const digits = q.replace(/\D/g, "");
	return (
		digits.length >= 4 &&
		String(lead.mobile_no || "")
			.replace(/\D/g, "")
			.includes(digits)
	);
}

// "today", "1 day", "12 days", "5 months" — how long the lead has been on file.
export function leadAge(created) {
	if (!created) return "";
	const days = Math.floor(
		(Date.now() - new Date(String(created).replace(" ", "T")).getTime()) / 86400000,
	);
	if (days <= 0) return "today";
	if (days === 1) return "1 day";
	if (days < 60) return `${days} days`;
	return `${Math.round(days / 30)} months`;
}
