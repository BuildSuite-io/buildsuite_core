// Approach 2 — disburse from the Petty Cash Request Desk form itself (the "less intrusive"
// alternative to posting a Journal Entry by hand). A Requested request shows a "Disburse"
// button; clicking it opens a dialog that mirrors the Vue app's disburse modal (amount,
// holder, and the Bank/Cash funding source). It calls the SAME server endpoint the Vue
// frontend uses — buildsuite_core.api.petty_cash.disburse → PettyCashRequest.disburse() —
// so the accounting (Dr Petty Cash [holder] / Cr source, holder on the dimension) is
// identical. No changes to the Journal Entry doctype.
frappe.ui.form.on("Petty Cash Request", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Requested") return;
		frm.add_custom_button(__("Disburse"), () => openDisburseDialog(frm)).addClass("btn-primary");
	},
});

function openDisburseDialog(frm) {
	// Funding sources: Bank/Cash accounts for the request's company, excluding Petty Cash
	// itself (the same list the Vue disburse modal shows).
	frappe.call({
		method: "buildsuite_core.api.petty_cash.list_cash_bank_accounts",
		args: { company: frm.doc.company },
	}).then(({ message }) => {
		const accounts = message || [];
		if (!accounts.length) {
			frappe.msgprint(__("No Bank/Cash account found for {0}.", [frm.doc.company]));
			return;
		}

		const amount = format_currency(frm.doc.amount, frappe.defaults.get_default("currency"));
		const dialog = new frappe.ui.Dialog({
			title: __("Disburse {0}", [amount]),
			fields: [
				{
					fieldtype: "HTML",
					options: `<p class="text-muted" style="margin-bottom:12px">${__("To")} <b>${frappe.utils.escape_html(frm.doc.requested_by || "")}</b> · ${__("posts a Journal Entry (Dr Petty Cash / Cr the source account).")}</p>`,
				},
				{
					fieldtype: "Select",
					fieldname: "paid_from",
					label: __("Pay from account"),
					reqd: 1,
					options: accounts.map((a) => a.name).join("\n"),
					default: accounts[0].name,
				},
			],
			primary_action_label: __("Disburse"),
			primary_action(values) {
				dialog.disable_primary_action();
				frappe.call({
					method: "buildsuite_core.api.petty_cash.disburse",
					args: { name: frm.doc.name, paid_from: values.paid_from },
					freeze: true,
					freeze_message: __("Posting disbursement…"),
				}).then(() => {
					dialog.hide();
					frappe.show_alert({ message: __("Disbursed — Journal Entry posted."), indicator: "green" });
					frm.reload_doc();
				}).catch(() => dialog.enable_primary_action());
			},
		});
		dialog.show();
	});
}
