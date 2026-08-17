# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The Site Execution report set was reworked to match the prototype's Overview reports:
Delay Analysis, Billing and Collection, Subcontractor Position, Material Status. This
replaces the old set (Project Status Summary, Completed Tasks, Pending Progress Entries,
Stage Plan vs Actual, Progress Entries) on sites seeded before the change — creates the
new Query Reports, repoints the Site Execution workspace tiles, and removes the retired
reports."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import REPORTS

RETIRED = (
	"Project Status Summary",
	"Completed Tasks",
	"Pending Progress Entries",
	"Stage Plan vs Actual",
	"Progress Entries",
)


def execute():
	# The four reports are now standard Script Reports (buildsuite_core/report/), synced from
	# their module files — no Query Report creation here. This patch only repoints the tiles.
	# Reset the Site Execution workspace tiles to the new report set (keep other workspaces).
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
		if r.workspace != "site-execution"
	]
	settings.set("reports", [])
	for row in kept:
		settings.append("reports", row)
	for name, icon, desc in REPORTS:
		settings.append(
			"reports",
			{"workspace": "site-execution", "report": name, "icon": icon, "description": desc},
		)
	settings.flags.ignore_permissions = True
	settings.save()

	# 3) Remove the retired reports (app-owned, now superseded).
	for name in RETIRED:
		if frappe.db.exists("Report", name):
			frappe.delete_doc("Report", name, ignore_permissions=True, force=True)
