# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted read/write for BuildSuite Core Settings (a Single doctype), so the
Vue Settings screen can persist org-wide settings server-side. Admin only."""

import frappe
from frappe import _

from buildsuite_core.overrides.project import (
	NAME_SERIES_MODE,
	PROJECT_ID_MODE,
)

ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}
SETTINGS = "BuildSuite Core Settings"
NAMING_MODES = [PROJECT_ID_MODE, NAME_SERIES_MODE]


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(_("Only an administrator can manage settings."), frappe.PermissionError)


def _project_series_options():
	"""Every naming series configured on the Project doctype."""
	field = frappe.get_meta("Project").get_field("naming_series")
	if field and field.options:
		return [row.strip() for row in field.options.split("\n") if row.strip()]
	return []


@frappe.whitelist()
def get_core_settings():
	"""Current settings + the choices the UI needs to render them."""
	_require_admin()
	return {
		"project_naming": frappe.db.get_single_value(SETTINGS, "project_naming") or PROJECT_ID_MODE,
		"project_naming_series": frappe.db.get_single_value(SETTINGS, "project_naming_series") or "",
		"project_naming_modes": NAMING_MODES,
		"project_series_options": _project_series_options(),
	}


@frappe.whitelist()
def set_project_naming(project_naming: str, project_naming_series: str = None):
	"""Set how new projects are named: the mode ('Project ID' | 'Name Series') and,
	for Name Series, the specific Project naming series."""
	_require_admin()
	if project_naming not in NAMING_MODES:
		frappe.throw(_("Project naming must be one of {0}.").format(", ".join(NAMING_MODES)))

	series = (project_naming_series or "").strip()
	if project_naming == NAME_SERIES_MODE:
		if series not in _project_series_options():
			frappe.throw(_("Unknown project naming series {0}.").format(series or "(blank)"))
	else:
		series = ""  # Project ID mode ignores the series

	doc = frappe.get_single(SETTINGS)
	doc.project_naming = project_naming
	doc.project_naming_series = series
	doc.flags.ignore_permissions = True
	doc.save()
	return {"project_naming": project_naming, "project_naming_series": series}
