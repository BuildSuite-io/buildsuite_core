// Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subcontractor Bill", {
	onload(frm) {
		// The Vue app links out to /app/subcontractor-bill/new?work_order=… — pick that up.
		if (frm.is_new() && !frm.doc.work_order && frappe.route_options && frappe.route_options.work_order) {
			frm.set_value("work_order", frappe.route_options.work_order);
			frappe.route_options = null;
		}
	},

	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.work_order) {
			frm.add_custom_button(__("Fetch from Work Order"), () => fetch_lines(frm));
		}
	},

	work_order(frm) {
		// Auto-derive this period's lines when the work order is chosen on a draft.
		if (frm.doc.docstatus === 0 && frm.doc.work_order) {
			fetch_lines(frm);
		}
	},
});

function fetch_lines(frm) {
	frm.call({
		doc: frm.doc,
		method: "fetch_lines",
		freeze: true,
		freeze_message: __("Deriving from certified Measurement Books…"),
	}).then((r) => {
		if (r && !r.exc) {
			frm.refresh_field("lines");
			frm.refresh_field("gross");
			frm.refresh_field("retention_amount");
			frm.refresh_field("net_payable");
		}
	});
}
