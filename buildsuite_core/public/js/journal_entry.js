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

// --- BOQ cost code on a JV expense line ------------------------------------------------------
// Charge an expense line to a BOQ cost code so its debit lands in BOQ actual
// (buildsuite_core.api.boq_actuals). Set the line's Project, then pick a Cost Code Type — a
// picker lists that project's Approved-BOQ codes (buildsuite_core.api.subcontract
// .get_project_cost_codes) and stamps the group / item / read-only label.
frappe.ui.form.on("Journal Entry Account", {
	custom_cost_code_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.custom_cost_code_type) {
			set_cost_code(cdt, cdn, {});
			return;
		}
		if (!row.project) {
			frappe.msgprint(__("Set the Project on this line first, then pick a cost code."));
			frappe.model.set_value(cdt, cdn, "custom_cost_code_type", "");
			return;
		}
		pick_cost_code(cdt, cdn, row.project, row.custom_cost_code_type);
	},

	project(frm, cdt, cdn) {
		// A code set against the old project is now stale — clear it.
		const row = locals[cdt][cdn];
		if (row.custom_cost_code_label) set_cost_code(cdt, cdn, {});
	},
});

function set_cost_code(cdt, cdn, c) {
	frappe.model.set_value(cdt, cdn, "custom_cost_code_group", c.group_code || "");
	frappe.model.set_value(cdt, cdn, "custom_cost_code_item", c.item_code || "");
	frappe.model.set_value(cdt, cdn, "custom_cost_code_label", c.label || "");
}

function pick_cost_code(cdt, cdn, project, type) {
	frappe.call({
		method: "buildsuite_core.api.subcontract.get_project_cost_codes",
		args: { project },
		callback: ({ message }) => {
			const codes = (message || []).filter((c) => c.type === type);
			if (!codes.length) {
				frappe.msgprint(__("No {0} cost codes on this project's Approved BOQ.", [type]));
				frappe.model.set_value(cdt, cdn, "custom_cost_code_type", "");
				return;
			}
			const d = new frappe.ui.Dialog({
				title: __("Pick Cost Code"),
				fields: [
					{
						fieldname: "code",
						fieldtype: "Select",
						label: __("Cost Code"),
						reqd: 1,
						options: codes.map((c) => c.label),
					},
				],
				primary_action_label: __("Select"),
				primary_action(values) {
					const c = codes.find((x) => x.label === values.code);
					if (c) set_cost_code(cdt, cdn, c);
					d.hide();
				},
			});
			// Abandoning the picker clears the half-set type.
			d.onhide = () => {
				if (!locals[cdt][cdn].custom_cost_code_label) {
					frappe.model.set_value(cdt, cdn, "custom_cost_code_type", "");
				}
			};
			d.show();
		},
	});
}
