"""Sales > Leads and quotations on existing sites: the Lead, Quotation and sales-master permissions,
the "Why we lose" (Lost Quotations) tile and report for the sales personas, and the lead sources.

Additive only (permissions.setup.grant_missing_sales_permissions): a role gets a default rule
only where it has none on that doctype, and a report only gains roles. Any permission a site has
already set, shipped or edited, is left exactly as it is; nothing is reset or deleted.
"""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Lead"):
		return
	from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import (
		seed_workspace_reports,
	)
	from buildsuite_core.install import seed_lead_sources
	from buildsuite_core.permissions.setup import grant_missing_sales_permissions

	# The "Why we lose" tile first (only into a Sales workspace with no report tiles yet), so the
	# report's roles below are checked against where it is tiled.
	seed_workspace_reports()
	grant_missing_sales_permissions()
	seed_lead_sources()
	for doctype in ("Lead", "Quotation"):
		frappe.clear_cache(doctype=doctype)
