# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The Subcontract workspace report tiles were reworked to real reports: Work Order Register,
Measurement Book Register and Subcontractor Bill Register are now standard Script Reports
(buildsuite_core/report/) rendered through the in-app report renderer, replacing the two former
tiles that deep-linked to the list views. This patch syncs the three Script Reports and repoints
the Subcontract workspace tiles on sites seeded before the change (the seeder is idempotent and
would otherwise leave the old tiles in place)."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import _SEED

MODULES = (
	"subcontractor_work_order_register",
	"measurement_book_register",
	"subcontractor_bill_register",
)


def execute():
	# 1) Ensure the three standard Script Reports are synced from their module files.
	for module in MODULES:
		frappe.reload_doc("buildsuite_core", "report", module, force=True)

	# 2) Repoint the Subcontract workspace tiles to the new report set (keep other workspaces).
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
		if r.workspace != "subcontract"
	]
	settings.set("reports", [])
	for row in kept:
		settings.append("reports", row)
	for row in _SEED["subcontract"]:
		settings.append("reports", {"workspace": "subcontract", **row})
	settings.flags.ignore_permissions = True
	settings.save()
