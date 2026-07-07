# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted read/write for BuildSuite Core Settings (a Single doctype), so the
Vue Settings screen can persist org-wide settings server-side."""

import frappe
from frappe import _

from buildsuite_core.overrides.project import (
	NAME_SERIES_MODE,
	PROJECT_ID_MODE,
	default_project_series,
	project_naming_mode,
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
	"""The org-wide settings for the admin Settings screen."""
	_require_admin()
	return {
		"project_naming": project_naming_mode(),
		"project_naming_modes": NAMING_MODES,
	}


@frappe.whitelist()
def set_project_naming(project_naming: str):
	"""Set the project naming MODE ('Project ID' | 'Name Series'). The specific series
	is chosen per-project on the New Project form, not here."""
	_require_admin()
	if project_naming not in NAMING_MODES:
		frappe.throw(_("Project naming must be one of {0}.").format(", ".join(NAMING_MODES)))
	doc = frappe.get_single(SETTINGS)
	doc.project_naming = project_naming
	doc.flags.ignore_permissions = True
	doc.save()
	return {"project_naming": project_naming}


@frappe.whitelist()
def get_project_naming():
	"""The naming mode + the series options the New Project form needs. Available to
	any signed-in user (anyone who can create a project), unlike the admin settings."""
	return {
		"project_naming": project_naming_mode(),
		"series_options": _project_series_options(),
		"default_series": default_project_series(),
	}
