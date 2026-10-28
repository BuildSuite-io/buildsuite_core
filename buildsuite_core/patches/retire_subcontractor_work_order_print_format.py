"""Retire the orphaned "Subcontractor Work Order" print format.

Two Work Order formats used to be seeded: this one (seed_print_assets.py) and "BuildSuite Work
Order" (print_formats.py), the latter set as the Subcontractor Work Order doctype's default
unconditionally. So this one was never the active default. It is no longer seeded, so remove the
leftover record — unless an admin has since deliberately made it the default on this site.
"""

import frappe

FORMAT = "Subcontractor Work Order"
DOCTYPE = "Subcontractor Work Order"


def execute():
	if not frappe.db.exists("Print Format", FORMAT):
		return
	# Respect a Desk choice: if an admin pinned this format as the doctype default, leave it be.
	default = frappe.db.get_value(
		"Property Setter",
		{"doc_type": DOCTYPE, "property": "default_print_format"},
		"value",
	)
	if default == FORMAT:
		return
	frappe.delete_doc("Print Format", FORMAT, ignore_permissions=True, force=True)
