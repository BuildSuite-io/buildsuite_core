# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Point the Project Finance workspace's Profit & Loss tile at our own account-tree P&L
(/project-finance/report/pnl, backed by api.finance_report.profit_and_loss) instead of the
stock ERPNext "Profit and Loss Statement". The whole workspace now uses our variant. The
seeder is idempotent per workspace (it leaves a workspace that already has rows untouched), so
this repoints the project-finance tiles explicitly on sites seeded before the change."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import (
	_project_finance_tiles,
)


def execute():
	if not frappe.db.exists("DocType", "Workspace Setting"):
		return
	settings = frappe.get_single("Workspace Setting")
	# Keep every other workspace's rows; rebuild only the project-finance tiles from the seeder.
	kept = [
		{
			"workspace": r.workspace,
			"label": r.label,
			"report": r.report,
			"route": r.route,
			"icon": r.icon,
			"description": r.description,
		}
		for r in settings.reports
		if r.workspace != "project-finance"
	]
	settings.set("reports", [])
	for row in kept:
		settings.append("reports", row)
	for row in _project_finance_tiles():
		settings.append("reports", {"workspace": "project-finance", **row})
	settings.flags.ignore_permissions = True
	settings.save()
