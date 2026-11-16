# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe


def seed_if_missing(doctype: str, filters: dict, values: dict | None = None):
	"""Create a record only when none matches `filters`, and never touch an existing one.

	The pattern for anything an app seeds on install or migrate: re-running it must not overwrite
	what an administrator changed in Desk. Returns the existing or the new document."""
	existing = frappe.db.get_value(doctype, filters, "name")
	if existing:
		return frappe.get_doc(doctype, existing)
	doc = frappe.get_doc({"doctype": doctype, **filters, **(values or {})})
	doc.flags.ignore_permissions = True
	return doc.insert()
