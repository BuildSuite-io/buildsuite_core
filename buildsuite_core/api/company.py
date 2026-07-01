# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist()
def get_default_company():
	"""The site's default company, used to pre-fill the project create form.

	Reads from the defaults cache (frappe.defaults) so any signed-in user can call
	it. The form previously hit frappe.client.get_value on the Global Defaults
	Single, which needs read perms that only System Manager holds by default — so
	every non-admin persona got a 403 (silently swallowed by the form).
	"""
	return frappe.defaults.get_global_default("default_company") or ""
