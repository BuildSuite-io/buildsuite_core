# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Finance reports, take two. Receivables & Payables and Financial Position are now
bespoke in-app Vue views (real data via api.finance_report, prototype layout) instead of the
flat Script Reports; the ERPNext tiles (Profit & Loss / Petty Cash / Expense Summary / Cash &
Bank) are pre-filtered to the site's company + relevant account so they open populated. This
repoints the Project Finance tiles on sites seeded before the change, and drops the two now-
orphaned Script Reports."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import (
	_project_finance_tiles,
)


def execute():
	# Repoint the Project Finance workspace tiles (keep the other workspaces' rows). The two
	# retired Script Reports (Receivables and Payables, Financial Position) are removed as
	# standard-report files, so migrate's orphan-report cleanup drops their docs — no tile
	# references them after this.
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
