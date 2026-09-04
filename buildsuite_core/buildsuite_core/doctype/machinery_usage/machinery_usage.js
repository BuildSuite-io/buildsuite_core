// Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Machinery Usage", {
	setup(frm) {
		frm.set_query("machine", () => ({ filters: { status: "Active" } }));
	},
});
