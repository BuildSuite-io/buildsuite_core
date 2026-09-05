"""Restore Subcontractor Work Order to the app's Expression naming.

Imported / live-data sites carried a naming override — a Property Setter, or a stale DocType row —
that names the Work Order via a **Naming Series**. But the doctype has no `naming_series` field and
the app names it by Expression (`SWO-.YYYY.-.#####`), so creating a WO on those sites fails with:

    AttributeError: 'SubcontractorWorkOrder' object has no attribute 'naming_series'

Remove the stray naming Property Setters and force the DocType row back to the app's Expression
rule. Existing (imported) records keep their names; new ones get SWO-YYYY-#####. No-op on sites that
were never overridden (e.g. a freshly-created one).
"""

import frappe

DOCTYPE = "Subcontractor Work Order"
APP_AUTONAME = "SWO-.YYYY.-.#####"


def execute():
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	stray = frappe.get_all(
		"Property Setter",
		filters={"doc_type": DOCTYPE, "property": ["in", ["autoname", "naming_rule", "naming_series"]]},
		pluck="name",
	)
	for ps in stray:
		frappe.delete_doc("Property Setter", ps, ignore_permissions=True, force=True)

	# Force the DocType row back to the app's naming, in case a stale row survived schema sync.
	current = frappe.db.get_value("DocType", DOCTYPE, ["autoname", "naming_rule"], as_dict=True)
	if not current or current.autoname != APP_AUTONAME or current.naming_rule != "Expression":
		frappe.db.set_value(
			"DocType",
			DOCTYPE,
			{"autoname": APP_AUTONAME, "naming_rule": "Expression"},
			update_modified=False,
		)

	if stray or (current and current.autoname != APP_AUTONAME):
		frappe.clear_cache(doctype=DOCTYPE)
		print(
			f"restore_subcontractor_work_order_naming: removed {len(stray)} naming Property Setter(s); "
			f"restored {APP_AUTONAME}"
		)
