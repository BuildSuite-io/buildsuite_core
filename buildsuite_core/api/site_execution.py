# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted read/write for the Site Execution workspace reports (Site Execution
Settings Single). The workspace reads the ordered report list; admins configure it."""

from urllib.parse import quote

import frappe
from frappe import _

ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}
SETTINGS = "Site Execution Settings"


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(_("Only an administrator can manage settings."), frappe.PermissionError)


def _report_route(report_name):
	"""Desk URL for a report, by its type."""
	meta = frappe.db.get_value(
		"Report", report_name, ["report_type", "ref_doctype"], as_dict=True
	)
	if not meta:
		return None
	if meta.report_type in ("Query Report", "Script Report"):
		return f"/app/query-report/{quote(report_name)}"
	doctype_route = frappe.scrub(meta.ref_doctype or "").replace("_", "-")
	return f"/app/{doctype_route}/view/report/{quote(report_name)}"


@frappe.whitelist()
def get_site_execution_reports():
	"""The ordered reports the Site Execution workspace should render. Available to
	any signed-in user (whoever can open the workspace)."""
	settings = frappe.get_single(SETTINGS)
	out = []
	for row in settings.reports:
		if not row.report or not frappe.db.exists("Report", row.report):
			continue
		out.append(
			{
				"report": row.report,
				"label": frappe.db.get_value("Report", row.report, "report_name") or row.report,
				"icon": row.icon or "file-text",
				"description": row.description or "",
				"route": _report_route(row.report),
			}
		)
	return out


@frappe.whitelist()
def get_site_execution_settings():
	"""The reports config for the admin settings screen."""
	_require_admin()
	settings = frappe.get_single(SETTINGS)
	return {
		"reports": [
			{"report": r.report, "icon": r.icon or "", "description": r.description or ""}
			for r in settings.reports
		]
	}


@frappe.whitelist()
def set_site_execution_reports(reports=None):
	"""Replace the workspace reports list (order preserved). Admin only."""
	_require_admin()
	reports = frappe.parse_json(reports) or []
	settings = frappe.get_single(SETTINGS)
	settings.set("reports", [])
	for row in reports:
		report = (row.get("report") or "").strip()
		if not report or not frappe.db.exists("Report", report):
			continue
		settings.append(
			"reports",
			{
				"report": report,
				"icon": (row.get("icon") or "").strip(),
				"description": (row.get("description") or "").strip(),
			},
		)
	settings.flags.ignore_permissions = True
	settings.save()
	return get_site_execution_settings()
