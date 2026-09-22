# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Backend permission anchors for the bespoke (custom-UI) reports.

Most reports are Frappe `Report` records, so their workspace tile is already role-gated by
`Report.is_permitted()`. The Project Finance, Procurement and Workforce reports (plus Delay
Analysis) are rendered by custom Vue components and were seeded as plain `route` tiles — which
bypassed permission entirely (any user who could open the workspace saw the tile and could
deep-link the route).

This module gives each of those a real `Report` record whose `roles` gate access, WITHOUT
changing how the frontend renders them: the workspace tile keeps its custom `route`, but
`workspace_setting._resolve` now hides it unless the anchor's `Report.is_permitted()` passes
(via ROUTE_TO_REPORT), and the SPA route guard denies a deep-link the same way
(api.permission.get_access_context exposes the permitted routes). So access is driven entirely by
the backend Report — no role, no tile, no route.

Anchors are Query Reports with roles but no query (the Vue component draws the UI; Frappe never
runs them). Seeded create-if-missing so an admin's later role edits survive migrate.
"""

import frappe

# Anchor Report records are namespaced so they never collide with an ERPNext/standard report of
# the same title (e.g. ERPNext ships a "Purchase Register" Script Report with its own roles). The
# name is backend-only — tiles and the Vue views keep their clean labels.
_REPORT_PREFIX = "BuildSuite "

# Every report also grants these, so admins always see everything.
_ADMIN_ROLES = ("BuildSuite Administrator", "System Manager")

# (report_name, ref_doctype, spa_route, roles) — the SPA route is the custom Vue view the tile
# opens; ref_doctype anchors the Report to its primary subject.
_REPORT_ANCHORS = (
	# --- Project Finance ---
	("Profit and Loss", "GL Entry", "/project-finance/report/pnl",
		("BuildSuite Accountant", "BuildSuite Director", "BuildSuite PM")),
	("Receivables and Payables", "Sales Invoice", "/project-finance/report/aged",
		("BuildSuite Accountant", "BuildSuite Director", "BuildSuite PM")),
	("Financial Position", "Account", "/project-finance/report/position",
		("BuildSuite Accountant", "BuildSuite Director", "BuildSuite PM")),
	("Expense Summary", "Expense Entry", "/project-finance/report/expenses",
		("BuildSuite Accountant", "BuildSuite Director", "BuildSuite PM")),
	("Cash and Bank Statement", "Account", "/project-finance/report/cashbank",
		("BuildSuite Accountant", "BuildSuite Director", "BuildSuite PM")),
	("Petty Cash Report", "Petty Cash Request", "/project-finance/report/petty",
		("BuildSuite Accountant", "BuildSuite Director", "BuildSuite PM",
		 "BuildSuite Site Engineer", "BuildSuite Foreman")),
	# --- Procurement ---
	("Requests Waiting to be Ordered", "Material Request", "/procurement/report/requests-to-order",
		("BuildSuite Procurement Officer", "BuildSuite Store Keeper", "BuildSuite PM", "BuildSuite Director")),
	("Delivery Follow-up", "Purchase Order", "/procurement/report/delivery-followup",
		("BuildSuite Procurement Officer", "BuildSuite Store Keeper", "BuildSuite PM", "BuildSuite Director")),
	("Material at Site", "Purchase Receipt", "/procurement/report/site-stock",
		("BuildSuite Procurement Officer", "BuildSuite Store Keeper", "BuildSuite PM", "BuildSuite Director")),
	("Purchase Rate vs Estimate", "Purchase Order", "/procurement/report/rate-check",
		("BuildSuite Procurement Officer", "BuildSuite Store Keeper", "BuildSuite PM", "BuildSuite Director")),
	("Purchase Register", "Purchase Order", "/procurement/report/purchase-register",
		("BuildSuite Procurement Officer", "BuildSuite Store Keeper", "BuildSuite PM", "BuildSuite Director")),
	("Consumption by Cost Code", "Stock Entry", "/procurement/report/consumption-by-cost-code",
		("BuildSuite Procurement Officer", "BuildSuite Store Keeper", "BuildSuite PM", "BuildSuite Director")),
	# --- Workforce ---
	("Labour Attendance Register", "Field Attendance", "/labour-attendance",
		("BuildSuite HR Manager", "BuildSuite Foreman", "BuildSuite PM", "BuildSuite Director")),
	("Overtime Attendance Register", "Field Attendance", "/overtime-attendance",
		("BuildSuite HR Manager", "BuildSuite Foreman", "BuildSuite PM", "BuildSuite Director")),
	("Site Attendance Summary", "Field Attendance", "/workforce/attendance-summary",
		("BuildSuite HR Manager", "BuildSuite Foreman", "BuildSuite PM", "BuildSuite Director")),
	# --- Site Execution ---
	("Delay Analysis", "Stage Planning", "/reports/delay-analysis",
		("BuildSuite PM", "BuildSuite Director", "BuildSuite Site Engineer")),
)

# custom SPA route -> its (namespaced) anchor Report name. The one map the tile-gate and
# route-guard share.
ROUTE_TO_REPORT = {route: _REPORT_PREFIX + name for name, _ref, route, _roles in _REPORT_ANCHORS}


def seed_report_anchors():
	"""Create the Report permission anchors if absent. Idempotent and non-clobbering: an existing
	Report (ours, or one an admin re-roled) is left untouched, so role edits survive migrate."""
	created = []
	for name, ref_doctype, _route, roles in _REPORT_ANCHORS:
		report_name = _REPORT_PREFIX + name
		if frappe.db.exists("Report", report_name):
			continue
		if not frappe.db.exists("DocType", ref_doctype):
			continue
		allowed = [r for r in (*roles, *_ADMIN_ROLES) if frappe.db.exists("Role", r)]
		doc = frappe.get_doc(
			{
				"doctype": "Report",
				"report_name": report_name,
				"report_type": "Query Report",
				"ref_doctype": ref_doctype,
				"is_standard": "No",
				# Rendered by a custom Vue component — Frappe never runs this, the record only
				# anchors permission (its roles) + subject (ref_doctype).
				"query": "",
				"roles": [{"role": r} for r in allowed],
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		created.append(report_name)
	return created


def is_route_permitted(route):
	"""Whether the current user may open a custom report route — its anchor Report grants a role
	they hold. Routes with no anchor (not a gated report) return True."""
	name = ROUTE_TO_REPORT.get(route)
	if not name:
		return True
	if not frappe.db.exists("Report", name):
		return True  # anchor not seeded yet — don't lock the report out
	return bool(frappe.get_cached_doc("Report", name).is_permitted())


def permitted_report_routes():
	"""The custom report routes the current user may open — for the SPA route guard + tiles."""
	return [route for route in ROUTE_TO_REPORT if is_route_permitted(route)]
