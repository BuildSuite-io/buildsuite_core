# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project naming override.

The Frappe record `name` for a Project is controlled by the BuildSuite Core
Settings "Project Naming" select:

  - "Project ID"  -> the name IS the entered Project ID (custom_project_id). The
                     field is already required + unique, so the id doubles as the
                     record key.
  - "Name Series" -> the name is generated from the naming series chosen in the
                     "Project Naming Series" setting (e.g. PROJ-.####), as ERPNext
                     would by default.

ERPNext's Project has no autoname() of its own (it relies on the naming_series
autoname rule), so defining one here takes precedence via override_doctype_class.
"""

import frappe
from frappe import _
from frappe.model.naming import set_name_by_naming_series

from erpnext.projects.doctype.project.project import Project as _ERPNextProject

PROJECT_ID_MODE = "Project ID"
NAME_SERIES_MODE = "Name Series"
SETTINGS = "BuildSuite Core Settings"


def project_naming_config():
	"""(mode, series) from the settings. Defaults to Project ID mode."""
	mode = frappe.db.get_single_value(SETTINGS, "project_naming") or PROJECT_ID_MODE
	series = frappe.db.get_single_value(SETTINGS, "project_naming_series")
	return mode, series


def _name_by_project_id(doc):
	project_id = (doc.get("custom_project_id") or "").strip()
	if not project_id:
		frappe.throw(_("Project ID is required."))
	doc.name = project_id


class BuildSuiteProject(_ERPNextProject):
	def autoname(self):
		mode, series = project_naming_config()
		if mode == NAME_SERIES_MODE and series:
			self.naming_series = series
			set_name_by_naming_series(self)
			return
		# Project ID mode (also the fallback when Name Series has no series set).
		_name_by_project_id(self)


def reject_duplicate_project_id(doc, method=None):
	"""In Project-ID naming mode the record name IS the Project ID, so a duplicate id
	collides on the primary key and would surface as a raw DB error. Reject it up
	front with a clean message (Frappe's own unique-field check can't catch it here,
	since it excludes the row whose name equals the id)."""
	if not doc.is_new():
		return
	mode, series = project_naming_config()
	if mode == NAME_SERIES_MODE and series:
		return  # named by series — id uniqueness is enforced by the field's own unique check
	project_id = (doc.get("custom_project_id") or "").strip()
	if project_id and frappe.db.exists("Project", project_id):
		frappe.throw(_("A project with ID {0} already exists.").format(project_id))
