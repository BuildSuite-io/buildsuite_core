# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""BuildSuite Tenders gained a lifecycle status: tenders made before it are drafts (empty values
only)."""

import frappe


def execute():
	for name in frappe.get_all("BuildSuite Tenders", filters={"status": ("in", ("", None))}, pluck="name"):
		frappe.db.set_value("BuildSuite Tenders", name, "status", "Draft", update_modified=False)
