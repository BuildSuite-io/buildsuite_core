# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Finance reports, take three. Petty Cash, Expense Summary and Cash & Bank are now
bespoke in-app Vue views (real data via api.finance_report / api.expense_entry, prototype
layout) instead of the pre-filtered General Ledger routes. Only Profit & Loss stays an ERPNext
report. This repoints the Project Finance tiles on sites seeded before the change."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import (
	_project_finance_tiles,
)


def execute():
	# Repoint only the project-finance tiles; leave the other workspaces' rows untouched.
	settings = frappe.get_single("Workspace Setting")
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
