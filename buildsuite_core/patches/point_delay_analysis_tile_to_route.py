# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Point the Site Execution 'Delay Analysis' workspace tile at the bespoke in-app view's
	route (/reports/delay-analysis) instead of referencing the flat Query Report. The report is
	now rendered by a dedicated view, so the Workspace Setting should read as a plain URL — which
	is also how new sites are seeded (seed_workspace_reports)."""
	if not frappe.db.has_column("Workspace Report", "route"):
		return
	settings = frappe.get_single("Workspace Setting")
	changed = False
	for r in settings.reports:
		if r.workspace == "site-execution" and (r.report or "") == "Delay Analysis":
			r.report = None
			r.route = "/reports/delay-analysis"
			r.label = r.label or "Delay Analysis"
			changed = True
	if changed:
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.db.commit()  # nosemgrep
