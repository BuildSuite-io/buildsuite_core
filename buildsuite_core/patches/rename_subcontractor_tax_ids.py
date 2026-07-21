# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Generalise the Subcontractor's India-specific tax fields to country-neutral ones.

`gstin` → `tax_id` (e.g. GSTIN in India, VAT No / TIN elsewhere) and `pan` →
`secondary_tax_id`, preserving stored values. Idempotent.

Handles both orderings robustly: if only the old column exists, rename it; if the doctype
sync has already created the new (empty) column, copy the data across and drop the old one."""

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	for old, new in (("gstin", "tax_id"), ("pan", "secondary_tax_id")):
		has_old = frappe.db.has_column("Subcontractor", old)
		has_new = frappe.db.has_column("Subcontractor", new)
		if has_old and not has_new:
			rename_field("Subcontractor", old, new)
		elif has_old and has_new:
			frappe.db.sql(
				f"update `tabSubcontractor` set `{new}` = `{old}` "
				f"where (`{new}` is null or `{new}` = '') and `{old}` is not null and `{old}` != ''"
			)
			frappe.db.sql_ddl(f"alter table `tabSubcontractor` drop column `{old}`")
