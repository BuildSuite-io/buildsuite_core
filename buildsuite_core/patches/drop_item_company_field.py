# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Remove the BuildSuite `company` field from Item.

Item is an org-wide ERPNext master reused across companies, like Supplier/Customer (which lost their
`company` field in patches.drop_party_company_field). Gating it with a BuildSuite `company` custom
field bought nothing and only blocked reuse, so the field is removed. Delete the Custom Field record
and drop the now-orphan column. Idempotent.
"""

import frappe


def execute():
	for cf in frappe.get_all("Custom Field", filters={"dt": "Item", "fieldname": "company"}, pluck="name"):
		frappe.delete_doc("Custom Field", cf, ignore_permissions=True, force=True)
	# delete_doc usually drops the column; belt-and-suspenders if it didn't.
	if "company" in frappe.db.get_table_columns("Item"):
		try:
			frappe.db.sql_ddl("alter table `tabItem` drop column `company`")
		except Exception:
			pass  # already gone (stale schema cache)
	frappe.clear_cache(doctype="Item")
