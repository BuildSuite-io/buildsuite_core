# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The Project Finance report tiles were reworked: Profit & Loss / Petty Cash / Expense Summary
/ Cash & Bank now ride the ERPNext reports (Desk query-report route), and Receivables & Payables
and Financial Position are bespoke Script Reports (buildsuite_core/report/) shown in-app —
replacing the six mock-data Vue stubs. This patch syncs the two Script Reports and repoints the
Project Finance workspace tiles on sites seeded before the change (the seeder is idempotent and
would otherwise leave the old tiles in place)."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import _SEED

MODULES = ("receivables_and_payables", "financial_position")


def execute():
	# 1) Ensure the two bespoke Script Reports are synced from their module files.
	for module in MODULES:
		frappe.reload_doc("buildsuite_core", "report", module, force=True)

	# 2) Repoint the Project Finance workspace tiles to the new set (keep other workspaces).
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
	for row in _SEED["project-finance"]:
		settings.append("reports", {"workspace": "project-finance", **row})
	settings.flags.ignore_permissions = True
	settings.save()
