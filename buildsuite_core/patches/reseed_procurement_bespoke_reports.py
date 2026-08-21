# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Procurement reports, take two. The three borrowed ERPNext report links (Stock Balance /
Stock Ledger / Item-wise Purchase Register) are replaced by six bespoke in-app Vue reports
computed from live records (api.procurement_report): requests-to-order, delivery-followup,
site-stock, rate-check, purchase-register, consumption-by-cost-code. This repoints the
Procurement workspace tiles on sites seeded before the change."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import _SEED


def execute():
	# Repoint only the procurement tiles; leave the other workspaces' rows untouched.
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
		if r.workspace != "procurement"
	]
	settings.set("reports", [])
	for row in kept:
		settings.append("reports", row)
	for row in _SEED["procurement"]:
		settings.append("reports", {"workspace": "procurement", **row})
	settings.flags.ignore_permissions = True
	settings.save()
