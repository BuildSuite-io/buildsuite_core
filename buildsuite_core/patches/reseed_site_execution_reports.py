# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The Site Execution report set was reworked to match the prototype's Overview reports
(Delay Analysis, Billing and Collection, Subcontractor Position, Material Status), replacing the
old set (Project Status Summary, Completed Tasks, Pending Progress Entries, Stage Plan vs Actual,
Progress Entries). This resets the Site Execution workspace tiles to the new set and removes the
retired reports on sites seeded before the change.

The report definitions now live as app-owned Script Reports (created on migrate), so this patch no
longer creates Query Reports itself — it was originally written against a since-removed
`_ensure_report` + 7-tuple `REPORTS`, which broke `bench migrate` on sites that migrate in later.
Rewritten to the current API: `REPORTS` is now `(name, icon, desc)` and Delay Analysis is a
bespoke in-app route."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import (
	DELAY_ANALYSIS_ROUTE,
	REPORTS,
)

RETIRED = (
	"Project Status Summary",
	"Completed Tasks",
	"Pending Progress Entries",
	"Stage Plan vs Actual",
	"Progress Entries",
)


def execute():
	# Reset the Site Execution tiles to the current report set, keeping every other workspace's.
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
		# Delay Analysis is a bespoke in-app view (a plain route); the rest reference Reports.
		row = (
			{"label": name, "route": DELAY_ANALYSIS_ROUTE, "icon": icon, "description": desc}
			if name == "Delay Analysis"
			else {"report": name, "icon": icon, "description": desc}
		)
		settings.append("reports", {"workspace": "site-execution", **row})
	settings.flags.ignore_permissions = True
	settings.save()

	# Remove the retired reports (app-owned, now superseded).
	for name in RETIRED:
		if frappe.db.exists("Report", name):
			frappe.delete_doc("Report", name, ignore_permissions=True, force=True)
