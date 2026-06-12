// Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stage Planning", {
	before_workflow_action(frm) {
		// Only intercept Reject — every other workflow action proceeds natively.
		if (frm.selected_workflow_action !== "Reject") return;

		// handle_workflow_action() freezes the screen before firing this hook; unfreeze
		// so the prompt is interactive. Returning a promise gates the native transition:
		// resolving lets apply_workflow run, rejecting aborts it.
		frappe.dom.unfreeze();

		return new Promise((resolve, reject) => {
			let submitted = false;
			const d = new frappe.ui.Dialog({
				title: __("Reject Stage"),
				fields: [
					{
						fieldname: "reason",
						fieldtype: "Small Text",
						label: __("Rejection Reason"),
						reqd: 1,
					},
				],
				primary_action_label: __("Reject"),
				primary_action(values) {
					submitted = true;
					d.hide();
					// Persist the reason before the transition. apply_workflow reloads the
					// doc from the DB, so the saved value is what validate() / the Rejected
					// state will carry.
					frm.set_value("reject_reason", values.reason);
					frm.save()
						.then(() => resolve())
						.catch((err) => reject(err));
				},
			});
			// Closing without submitting (Cancel / Esc / X) aborts the rejection.
			d.on_hide = () => {
				if (!submitted) reject();
			};
			d.show();
		});
	},
});
