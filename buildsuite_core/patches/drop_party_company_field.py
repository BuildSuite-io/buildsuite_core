# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Remove the BuildSuite `company` field from the Supplier and Customer parties.

ERPNext parties are global masters: a single Supplier/Customer transacts with any company, and the
per-company payable/receivable account lives in the native Party Account (`accounts`) child table.
Gating them with a BuildSuite `company` custom field blocked reusing a party across procurement +
finance (an assembly-style cross-company bug), so the field is removed. Delete the Custom Field
records and drop the now-orphan columns. Idempotent; Item keeps its company field.
"""

import frappe


def execute():
	for dt in ("Supplier", "Customer"):
		for cf in frappe.get_all(
			"Custom Field", filters={"dt": dt, "fieldname": "company"}, pluck="name"
		):
			frappe.delete_doc("Custom Field", cf, ignore_permissions=True, force=True)
		# delete_doc usually drops the column; belt-and-suspenders if it didn't.
		if "company" in frappe.db.get_table_columns(dt):
			try:
				frappe.db.sql_ddl(f"alter table `tab{dt}` drop column `company`")
			except Exception:
				pass  # already gone (stale schema cache)
		frappe.clear_cache(doctype=dt)
