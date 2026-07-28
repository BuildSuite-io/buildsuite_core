# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Company scope for the SPA. Single-company for now — see the single-company seam."""

import frappe

from buildsuite_core.utils.project import default_company


@frappe.whitelist()
def active_company():
	"""The company finance transactions (and their pickers) are scoped to right now.

	Same resolver the server-side company guards use, so the frontend picker filters agree
	with them. `window.sysdefaults.company` is not reliably present (e.g. the standalone Vite
	dev server), so the SPA fetches this instead. Multi-company later: derive from context.
	"""
	return default_company()
