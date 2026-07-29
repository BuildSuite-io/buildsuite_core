// Petty cash disbursement, posted by hand in Desk (bigger teams that skip the Vue app).
// Pick a Petty Cash Request in the `petty_cash_request` field and this prefills the company,
// the amount, and the Petty Cash outflow line (Dr Petty Cash, holder stamped). The accountant
// only has to add the Cr Bank/Cash source. On submit the server hooks flip the request to
// Disbursed (buildsuite_core.utils.petty_cash). Only Requested requests are selectable.
frappe.ui.form.on("Journal Entry", {
	setup(frm) {
		frm.set_query("petty_cash_request", () => ({ filters: { status: "Requested" } }));
	},

	petty_cash_request(frm) {
		const request = frm.doc.petty_cash_request;
		if (!request) return;

		frappe.call({
			method: "buildsuite_core.api.petty_cash.disbursement_prefill",
			args: { request },
			callback: ({ message }) => {
				if (!message) return;

				const prefill = () => {
					// Reuse an existing Petty Cash line if one is already there, else add one.
					let row = (frm.doc.accounts || []).find((a) => a.account === message.petty_cash_account);
					if (!row) row = frm.add_child("accounts");
					frappe.model.set_value(row.doctype, row.name, "account", message.petty_cash_account);
					frappe.model.set_value(row.doctype, row.name, "debit_in_account_currency", message.amount);
					frappe.model.set_value(row.doctype, row.name, "credit_in_account_currency", 0);
					if (message.employee) frappe.model.set_value(row.doctype, row.name, "employee", message.employee);
					if (message.remark && !frm.doc.user_remark) frm.set_value("user_remark", message.remark);
					frm.refresh_field("accounts");
				};

				// Set the company first — changing it can clear the accounts grid, so prefill after.
				if (message.company && frm.doc.company !== message.company) {
					frm.set_value("company", message.company).then(prefill);
				} else {
					prefill();
				}
			},
		});
	},
});
