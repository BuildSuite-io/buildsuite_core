# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist()
def get_default_company():
	"""The site's default company (Global Defaults → Default Company), used to
	pre-fill the project create form.

	Reads the Global Defaults `default_company` field directly. `frappe.db.get_single_value`
	is a raw DB read (no client-side permission check), so it works for every persona —
	unlike `frappe.client.get_value` on the Single, which 403s for non-admins. We do NOT
	use `get_global_default("default_company")`: the Single registers its value under the
	`company` key, so that lookup returns None even when a default company is set. The
	`company` global default is kept only as a fallback.
	"""
	return (
		frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.defaults.get_global_default("company")
		or ""
	)
