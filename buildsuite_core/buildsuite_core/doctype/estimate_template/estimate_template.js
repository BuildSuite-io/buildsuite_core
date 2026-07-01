// Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Estimate Template Row", {
	line_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.line_type === "Assembly") {
			frappe.model.set_value(cdt, cdn, "resource", null);
		} else if (row.line_type === "Resource") {
			frappe.model.set_value(cdt, cdn, "assembly", null);
		}
		frappe.model.set_value(cdt, cdn, "uom", null);
		frappe.model.set_value(cdt, cdn, "rate", 0);
		frappe.model.set_value(cdt, cdn, "amount", 0);
		frappe.model.set_value(cdt, cdn, "description", null);
	},

	assembly(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.assembly) return;
		frappe.db
			.get_value("Assembly", row.assembly, ["assembly_name", "uom", "rate_per_unit"])
			.then((r) => {
				const d = r.message || {};
				frappe.model.set_value(cdt, cdn, "uom", d.uom);
				frappe.model.set_value(cdt, cdn, "description", d.assembly_name);
				const rate = d.rate_per_unit || 0;
				frappe.model.set_value(cdt, cdn, "rate", rate);
				frappe.model.set_value(cdt, cdn, "amount", (row.placeholder_qty || 0) * rate);
			});
	},

	resource(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.resource) return;
		frappe.db
			.get_value("Construction Rate Master", row.resource, [
				"rate_name",
				"uom",
				"current_rate",
			])
			.then((r) => {
				const d = r.message || {};
				frappe.model.set_value(cdt, cdn, "uom", d.uom);
				frappe.model.set_value(cdt, cdn, "description", d.rate_name);
				const rate = d.current_rate || 0;
				frappe.model.set_value(cdt, cdn, "rate", rate);
				frappe.model.set_value(cdt, cdn, "amount", (row.placeholder_qty || 0) * rate);
			});
	},

	placeholder_qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "amount", (row.placeholder_qty || 0) * (row.rate || 0));
	},
});
