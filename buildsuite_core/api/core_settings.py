# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted read/write for BuildSuite Core Settings (a Single doctype), so the
Vue Settings screen can persist org-wide settings server-side. Admin only."""

import frappe
from frappe import _

from buildsuite_core.overrides.project import PROJECT_ID_MODE

ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}
SETTINGS = "BuildSuite Core Settings"


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(_("Only an administrator can manage settings."), frappe.PermissionError)


def _project_naming_options():
	"""'Project ID' plus every naming series configured on the Project doctype."""
	options = [PROJECT_ID_MODE]
	field = frappe.get_meta("Project").get_field("naming_series")
	if field and field.options:
		options += [row.strip() for row in field.options.split("\n") if row.strip()]
	return options


@frappe.whitelist()
def get_core_settings():
	"""Current settings + the choices the UI needs to render them."""
	_require_admin()
	naming = frappe.db.get_single_value(SETTINGS, "project_naming") or PROJECT_ID_MODE
	return {
		"project_naming": naming,
		"project_naming_options": _project_naming_options(),
	}


@frappe.whitelist()
def set_project_naming(project_naming: str):
	"""Set how new projects are named. Must be 'Project ID' or a known Project series."""
	_require_admin()
	if project_naming not in _project_naming_options():
		frappe.throw(_("Unknown project naming option {0}.").format(project_naming))
	doc = frappe.get_single(SETTINGS)
	doc.project_naming = project_naming
	doc.flags.ignore_permissions = True
	doc.save()
	return {"project_naming": project_naming}
