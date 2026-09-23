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
# All anchors live under the app's own module so admins find them in one place in the Report list.
_ANCHOR_MODULE = "BuildSuite Core"

# Every report also grants these, so admins always see everything.
_ADMIN_ROLES = ("BuildSuite Administrator", "System Manager")

# (report_name, ref_doctype, spa_route, roles) — the SPA route is the custom Vue view the tile
# opens; ref_doctype anchors the Report to its primary subject. Roles are persona roles only; the
# seeder appends _ADMIN_ROLES so admins always see everything. Kept in step with the access matrix.
_REPORT_ANCHORS = (
	# --- Project Finance ---
	("Profit and Loss", "GL Entry", "/project-finance/report/pnl",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Accountant")),
	("Receivables and Payables", "Sales Invoice", "/project-finance/report/aged",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Accountant")),
	("Financial Position", "Account", "/project-finance/report/position",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Accountant")),
	("Expense Summary", "Expense Entry", "/project-finance/report/expenses",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Accountant")),
	("Cash and Bank Statement", "Account", "/project-finance/report/cashbank",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Accountant")),
	# Petty Cash is visible to every persona (matrix).
	("Petty Cash Report", "Petty Cash Request", "/project-finance/report/petty",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Estimator", "BuildSuite QS",
		 "BuildSuite Site Engineer", "BuildSuite Foreman", "BuildSuite Procurement Officer",
		 "BuildSuite Store Keeper", "BuildSuite Accountant", "BuildSuite HR Manager")),
	# --- Procurement ---
	("Requests Waiting to be Ordered", "Material Request", "/procurement/report/requests-to-order",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Site Engineer",
		 "BuildSuite Procurement Officer", "BuildSuite Store Keeper")),
	("Delivery Follow-up", "Purchase Order", "/procurement/report/delivery-followup",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Site Engineer",
		 "BuildSuite Procurement Officer", "BuildSuite Store Keeper")),
	("Material at Site", "Purchase Receipt", "/procurement/report/site-stock",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Site Engineer",
		 "BuildSuite Procurement Officer", "BuildSuite Store Keeper")),
	("Purchase Rate vs Estimate", "Purchase Order", "/procurement/report/rate-check",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Estimator", "BuildSuite QS",
		 "BuildSuite Procurement Officer", "BuildSuite Accountant")),
	("Purchase Register", "Purchase Order", "/procurement/report/purchase-register",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Procurement Officer", "BuildSuite Accountant")),
	("Consumption by Cost Code", "Stock Entry", "/procurement/report/consumption-by-cost-code",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Procurement Officer", "BuildSuite Accountant")),
	# --- Workforce ---
	("Labour Attendance Register", "Field Attendance", "/labour-attendance",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Accountant", "BuildSuite HR Manager")),
	("Overtime Attendance Register", "Field Attendance", "/overtime-attendance",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Accountant", "BuildSuite HR Manager")),
	("Site Attendance Summary", "Field Attendance", "/workforce/attendance-summary",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite Accountant", "BuildSuite HR Manager")),
	# --- Site Execution ---
	("Delay Analysis", "Stage Planning", "/reports/delay-analysis",
		("BuildSuite Director", "BuildSuite PM", "BuildSuite QS", "BuildSuite Site Engineer")),
)

# File-based Script Reports carry their roles in their own report .json (the fresh-install
# default, synced on migrate). Mirrored here — persona roles only, admin appended — so the
# one-time re-baseline patch can reset EXISTING sites in the same pass as the anchors.
_FILE_REPORT_ROLES = {
	"Subcontractor Work Order Register": ("BuildSuite Director", "BuildSuite PM", "BuildSuite QS",
		"BuildSuite Site Engineer", "BuildSuite Procurement Officer", "BuildSuite Accountant"),
	"Measurement Book Register": ("BuildSuite Director", "BuildSuite PM", "BuildSuite QS",
		"BuildSuite Site Engineer"),
	"Subcontractor Bill Register": ("BuildSuite Director", "BuildSuite PM", "BuildSuite QS",
		"BuildSuite Procurement Officer", "BuildSuite Accountant"),
	"Client Bill Register": ("BuildSuite Director", "BuildSuite PM", "BuildSuite QS", "BuildSuite Accountant"),
	"Subcontractor Ledger": ("BuildSuite Director", "BuildSuite PM", "BuildSuite Procurement Officer",
		"BuildSuite Accountant"),
	"Cost Code Variance": ("BuildSuite Director", "BuildSuite PM", "BuildSuite Accountant"),
	"Billing and Collection": ("BuildSuite Director", "BuildSuite PM", "BuildSuite Accountant"),
	"Subcontractor Position": ("BuildSuite Director", "BuildSuite PM", "BuildSuite Accountant"),
	"Material Status": ("BuildSuite Director", "BuildSuite PM", "BuildSuite Site Engineer",
		"BuildSuite Foreman"),
}

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
			# Re-home an existing anchor: a Report with a ref_doctype but no explicit module
			# inherits the ref_doctype's module, scattering our anchors across Accounts / Buying /
			# Stock. Pull them all under one module so an admin finds them in one place.
			if frappe.db.get_value("Report", report_name, "module") != _ANCHOR_MODULE:
				frappe.db.set_value("Report", report_name, "module", _ANCHOR_MODULE)
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
				# Group every anchor under the app's own module — otherwise Frappe defaults the
				# module to the ref_doctype's (Accounts, Buying, Stock, …) and they scatter.
				"module": _ANCHOR_MODULE,
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


def _matrix_roles():
	"""report_name -> the full role set (persona roles + admin) for every gated report — anchors
	and file-based Script Reports alike. The single source the re-baseline patch reads."""
	out = {_REPORT_PREFIX + name: tuple(roles) + _ADMIN_ROLES for name, _r, _rt, roles in _REPORT_ANCHORS}
	out.update({name: tuple(roles) + _ADMIN_ROLES for name, roles in _FILE_REPORT_ROLES.items()})
	return out


def reset_report_roles_to_matrix():
	"""Re-baseline every gated report's roles to the matrix. Run ONCE by a patch to bring existing
	sites in line: the seeder is create-if-missing, so a role change in _REPORT_ANCHORS never
	reaches a site that already has the anchor, and file-based .json role edits only reach a site
	if its report sync re-imports them. Idempotent — sets each Report's Has Role rows to exactly the
	matrix set and skips one already correct. Returns the reports whose roles changed."""
	changed = []
	for report_name, roles in _matrix_roles().items():
		if not frappe.db.exists("Report", report_name):
			continue
		allowed = [r for r in roles if frappe.db.exists("Role", r)]
		doc = frappe.get_doc("Report", report_name)
		if {r.role for r in doc.roles} == set(allowed):
			continue
		doc.set("roles", [{"role": r} for r in allowed])
		doc.flags.ignore_permissions = True
		doc.save()
		changed.append(report_name)
	return changed


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
