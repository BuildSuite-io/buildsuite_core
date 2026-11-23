# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Procurement > Request for Quotation, Supplier Quotation and their comparison, on existing sites.

Gives the Director, the Procurement Officer and the admin their default permissions on the two
doctypes (only where a role has no rule there yet), creates the Supplier Quotation Comparison
report's access anchor, and adds its tile to a Procurement workspace that already has report
tiles (after "Purchase rate vs estimate" where that is still there, else at the end). A workspace
with no tiles yet gets the whole default set, tile included.

Additive and idempotent: a permission or tile a site already has, shipped or edited, is left
exactly as it is. The custom fields and the "Request for Quotation" terms category sync on
migrate from custom_property_list; the print format is seeded by install.seed_master_data.
"""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import (
	SUPPLIER_QUOTATION_COMPARISON_TILE,
	seed_workspace_reports,
)
from buildsuite_core.permissions.setup import RFQ_DOCTYPES, grant_missing_rfq_permissions
from buildsuite_core.report_access import seed_report_anchors

_AFTER_ROUTE = "/procurement/report/rate-check"


def execute():
	if not frappe.db.exists("DocType", "Request for Quotation"):
		return
	grant_missing_rfq_permissions()
	seed_report_anchors()
	_add_comparison_tile()
	for doctype in RFQ_DOCTYPES:
		frappe.clear_cache(doctype=doctype)


def _add_comparison_tile():
	settings = frappe.get_single("Workspace Setting")
	tile = SUPPLIER_QUOTATION_COMPARISON_TILE
	mine = [r for r in settings.reports if r.workspace == "procurement"]
	if not mine:
		seed_workspace_reports()  # no Procurement tiles yet: the default set carries this one
		return
	if any((r.route or "").strip() == tile["route"] for r in mine):
		return
	rows = [r.as_dict(no_default_fields=True) for r in settings.reports]
	at = next(
		(
			i + 1
			for i, r in enumerate(rows)
			if r.get("workspace") == "procurement" and (r.get("route") or "").strip() == _AFTER_ROUTE
		),
		None,
	)
	if at is None:
		at = max(i for i, r in enumerate(rows) if r.get("workspace") == "procurement") + 1
	rows.insert(at, {**tile, "workspace": "procurement"})
	settings.set("reports", [])
	for r in rows:
		settings.append("reports", r)
	settings.flags.ignore_permissions = True
	settings.save()
