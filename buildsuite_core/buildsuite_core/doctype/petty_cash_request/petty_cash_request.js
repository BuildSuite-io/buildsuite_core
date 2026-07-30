// Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
// For license information, please see license.txt

// A disbursed petty cash request has posted a Journal Entry — surface a "View" action group
// (Ledger + Journal Entry) for it, mirroring the Expense Entry form. Only shown once the
// request is Disbursed (has a posted JE).
frappe.ui.form.on("Petty Cash Request", {
	refresh(frm) {
		if (frm.doc.status !== "Disbursed" || !frm.doc.journal_entry) return;

		frm.add_custom_button(
			__("Ledger"),
			() =>
				frappe.set_route("query-report", "General Ledger", {
					company: frm.doc.company,
					voucher_no: frm.doc.journal_entry,
					from_date: frm.doc.request_date,
					to_date: frm.doc.request_date,
					group_by: "Group by Voucher (Consolidated)",
				}),
			__("View"),
		);

		frm.add_custom_button(
			__("Journal Entry"),
			() => frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry),
			__("View"),
		);
	},
});
