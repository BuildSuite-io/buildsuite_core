# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted read/write for per-workspace **report-style shortcut** tiles
(Workspace Setting Single). Each live BuildSuite workspace renders an ordered list
of report tiles; admins configure them per workspace in the Workspace Setting screen.

A tile's destination is either an explicit `route` (an in-app path like
`/subcontractor-work-orders`, or a Desk URL like `/app/query-report/Stock Balance`)
or a linked Frappe `Report` (whose Desk route + name are derived when `route` is blank)."""

from urllib.parse import quote

import frappe
from frappe import _

ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}
SETTINGS = "Workspace Setting"

# The live BuildSuite workspaces that expose a configurable Reports group.
WORKSPACES = (
	{"slug": "site-execution", "label": "Site Execution"},
	{"slug": "estimation", "label": "Estimation"},
	{"slug": "procurement", "label": "Procurement"},
	{"slug": "subcontract", "label": "Subcontract"},
)
_SLUGS = {w["slug"] for w in WORKSPACES}


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(_("Only an administrator can manage settings."), frappe.PermissionError)


def _report_route(report_name):
	"""Route for a report tile. Query/Script Reports render IN-APP via the generic
	FrappeReport renderer (/reports/view/<name>); Report Builder reports have no in-app
	renderer, so they still open on the Desk."""
	meta = frappe.db.get_value("Report", report_name, ["report_type", "ref_doctype"], as_dict=True)
	if not meta:
		return None
	if meta.report_type in ("Query Report", "Script Report"):
		return f"/reports/view/{quote(report_name)}"
	doctype_route = frappe.scrub(meta.ref_doctype or "").replace("_", "-")
	return f"/app/{doctype_route}/view/report/{quote(report_name)}"


def _resolve(row):
	"""A stored row → a renderable tile, or None if it has no valid destination.
	Explicit `route` wins; otherwise derive route + label from the linked Report."""
	label = (row.get("label") or "").strip()
	route = (row.get("route") or "").strip()
	report = (row.get("report") or "").strip()
	if not route and report:
		if not frappe.db.exists("Report", report):
			return None
		route = _report_route(report)
		label = label or frappe.db.get_value("Report", report, "report_name") or report
	if not route:
		return None
	return {
		"label": label or route,
		"route": route,
		"icon": (row.get("icon") or "file-text").strip() or "file-text",
		"description": (row.get("description") or "").strip(),
		# External = a Desk URL or absolute link (opened via <a>, not the SPA router).
		"external": route.startswith("/app/") or "://" in route,
	}


@frappe.whitelist()
def get_workspace_reports(workspace):
	"""Ordered, renderable report tiles for a workspace. Any signed-in user (whoever
	can open the workspace)."""
	if workspace not in _SLUGS:
		return []
	settings = frappe.get_single(SETTINGS)
	out = []
	for row in settings.reports:
		if row.workspace != workspace:
			continue
		tile = _resolve(row.as_dict())
		if tile:
			out.append(tile)
	return out


@frappe.whitelist()
def get_workspace_settings():
	"""Every live workspace + its configured report rows, for the admin screen."""
	_require_admin()
	settings = frappe.get_single(SETTINGS)
	by_ws = {w["slug"]: [] for w in WORKSPACES}
	for row in settings.reports:
		if row.workspace in by_ws:
			by_ws[row.workspace].append(
				{
					"label": row.label or "",
					"report": row.report or "",
					"route": row.route or "",
					"icon": row.icon or "",
					"description": row.description or "",
				}
			)
	return {"workspaces": list(WORKSPACES), "reports": by_ws}


@frappe.whitelist()
def set_workspace_reports(workspace, reports=None):
	"""Replace one workspace's report rows (order preserved), leaving other
	workspaces' rows untouched. Admin only."""
	_require_admin()
	if workspace not in _SLUGS:
		frappe.throw(_("Unknown workspace: {0}").format(workspace))
	reports = frappe.parse_json(reports) or []
	settings = frappe.get_single(SETTINGS)

	# Preserve the other workspaces' rows; rebuild this workspace's from the payload.
	kept = [r for r in settings.reports if r.workspace != workspace]
	settings.set("reports", [])
	for r in kept:
		settings.append(
			"reports",
			{
				"workspace": r.workspace,
				"label": r.label,
				"report": r.report,
				"route": r.route,
				"icon": r.icon,
				"description": r.description,
			},
		)
	for row in reports:
		report = (row.get("report") or "").strip()
		route = (row.get("route") or "").strip()
		if not (report or route):
			continue
		settings.append(
			"reports",
			{
				"workspace": workspace,
				"label": (row.get("label") or "").strip(),
				"report": report,
				"route": route,
				"icon": (row.get("icon") or "").strip(),
				"description": (row.get("description") or "").strip(),
			},
		)
	settings.flags.ignore_permissions = True
	settings.save()
	return get_workspace_settings()
