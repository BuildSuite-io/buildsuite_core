# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Labour Cost Summary joins the Workforce reports, first in the list.

Creates its access anchor (same roles as Site Attendance Summary), puts the Workforce report tiles
in the order Labour Cost Summary, Site Attendance Summary, Labour Attendance Register, Overtime
Attendance Register (keeping any description an admin edited), and removes "Labour cost from
timesheets" - its Report and its tile - if the site has it. Idempotent."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import _SEED
from buildsuite_core.report_access import seed_report_anchors

REMOVED = "Labour cost from timesheets"


def execute():
	seed_report_anchors()

	for name in frappe.get_all("Report", filters={"report_name": REMOVED}, pluck="name"):
		frappe.delete_doc("Report", name, force=True, ignore_permissions=True)

	settings = frappe.get_single("Workspace Setting")
	mine = {r.label: r for r in settings.reports if r.workspace == "workforce"}
	others = [r for r in settings.reports if r.workspace != "workforce"]
	settings.set("reports", [])
	for r in others:
		settings.append("reports", r.as_dict(no_default_fields=True))
	for seed in _SEED["workforce"]:
		kept = mine.get(seed["label"])
		settings.append(
			"reports",
			{**seed, **(kept.as_dict(no_default_fields=True) if kept else {}), "workspace": "workforce"},
		)
	settings.flags.ignore_permissions = True
	settings.save()
