# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe

# Report name -> its standard Script Report module folder (buildsuite_core/report/<module>/).
MODULES = {
	"Delay Analysis": "delay_analysis",
	"Billing and Collection": "billing_and_collection",
	"Subcontractor Position": "subcontractor_position",
	"Material Status": "material_status",
}


def execute():
	"""These four Site Execution reports were dynamically-seeded Query Reports whose
	'%(project)s = "" OR …' SQL crashed the moment Frappe ran them with empty filters (which it
	does on page load — a Query Report substitutes filters via `query % filters`, so a missing
	key raises). They're now standard Script Reports (buildsuite_core/report/) whose execute()
	binds the project/date conditions only when set. Drop the old non-standard Report docs so the
	file-based Script Reports take their place, then (re)sync them."""
	for name, module in MODULES.items():
		if frappe.db.exists("Report", name) and frappe.db.get_value("Report", name, "is_standard") != "Yes":
			frappe.delete_doc("Report", name, force=True, ignore_permissions=True)
		frappe.reload_doc("buildsuite_core", "report", module, force=True)
	frappe.db.commit()  # nosemgrep
