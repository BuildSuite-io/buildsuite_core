# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Three new Subcontract-workspace reports — Client Bill Register, Subcontractor Ledger and Cost
Code Variance — were added as standard Script Reports (buildsuite_core/report/). The workspace
seeder is install-only (it skips a workspace that already has tiles), so sites seeded before this
change keep only the original three tiles. This patch syncs the new Script Reports and re-reconciles
the Subcontract tiles from the (now six-strong) _SEED set, leaving every other workspace untouched."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import _SEED

MODULES = (
	"client_bill_register",
	"subcontractor_ledger",
	"cost_code_variance",
)


def execute():
	# 1) Sync the three new standard Script Reports from their module files.
	for module in MODULES:
		frappe.reload_doc("buildsuite_core", "report", module, force=True)

	# 2) Rebuild the Subcontract workspace tiles from _SEED (keep every other workspace as-is).
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
