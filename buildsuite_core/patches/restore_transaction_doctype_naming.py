"""Restore Subcontractor Bill / Measurement Book to the app's Expression naming.

Same class as restore_subcontractor_work_order_naming (#252), extended to the other transaction
doctypes an import can break. These name by Expression and have NO `naming_series` field, but an
imported/live-data site carried a naming override (a Property Setter or stale DocType row) that
names them via a Naming Series — so creating one fails with:

    AttributeError: '<Doctype>' object has no attribute 'naming_series'

Remove the stray naming Property Setters and restore the app's Expression rule. Existing records
keep their names; new ones follow the app series. No-op on already-correct sites.
"""

import frappe

# doctype -> the app's autoname (Expression rule, no naming_series field)
AUTONAMES = {
	"Subcontractor Work Order": "SWO-.YYYY.-.#####",
	"Subcontractor Bill": "SB-.YYYY.-.#####",
	"Measurement Book": "MB-.YYYY.-.#####",
}


def execute():
	for dt, autoname in AUTONAMES.items():
		if not frappe.db.exists("DocType", dt):
			continue
		stray = frappe.get_all(
			"Property Setter",
			filters={"doc_type": dt, "property": ["in", ["autoname", "naming_rule", "naming_series"]]},
			pluck="name",
		)
		for ps in stray:
			frappe.delete_doc("Property Setter", ps, ignore_permissions=True, force=True)

		current = frappe.db.get_value("DocType", dt, ["autoname", "naming_rule"], as_dict=True)
		if not current or current.autoname != autoname:
			frappe.db.set_value(
				"DocType", dt, {"autoname": autoname, "naming_rule": "Expression"}, update_modified=False
			)
		if stray or (current and current.autoname != autoname):
			frappe.clear_cache(doctype=dt)
			print(f"restore_transaction_doctype_naming: {dt} — removed {len(stray)} PS; restored {autoname}")
