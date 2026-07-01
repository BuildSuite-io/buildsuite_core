# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Recase the module display name "Buildsuite Core" -> "BuildSuite Core".

	MariaDB's default collation is case-insensitive, so `bench migrate` treats the
	two spellings as the same Module Def key and never rewrites the stored casing —
	the DB keeps the original "Buildsuite Core". `frappe.rename_doc` can't fix it
	either (it sees the target as already existing). Force the casing with direct
	SQL on the name/module columns.

	Idempotent, and a no-op on fresh installs where the record is already correctly
	cased (the module is created from modules.txt with the new spelling).
	"""
	old, new = "Buildsuite Core", "BuildSuite Core"

	if not frappe.db.exists("Module Def", old):
		return

	# Module Def's `name` is the PK; `module_name` is the separate display field —
	# recase both.
	frappe.db.sql("update `tabModule Def` set name = %s where name = %s", (new, old))
	frappe.db.sql("update `tabModule Def` set module_name = %s where module_name = %s", (new, old))

	# Recase the `module` value wherever it is stored so links stay consistent.
	for dt in (
		"DocType",
		"Report",
		"Page",
		"Workspace",
		"Dashboard",
		"Number Card",
		"Module Onboarding",
		"Web Form",
		"Print Format",
		"Notification",
		"Server Script",
		"Client Script",
		"Custom HTML Block",
	):
		if frappe.db.table_exists(dt) and frappe.db.has_column(dt, "module"):
			frappe.db.sql(f"update `tab{dt}` set module = %s where module = %s", (new, old))

	frappe.clear_cache()
