# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project naming override.

The Frappe record `name` for a Project is controlled by the BuildSuite Core
Settings "Project Naming" option:

  - "Project ID"  -> the name IS the entered Project ID (custom_project_id). The
                     field is already required + unique, so the id doubles as the
                     record key.
  - anything else -> treated as an ERPNext naming series (e.g. PROJ-.####), and
                     the name is generated from it as ERPNext would by default.

ERPNext's Project has no autoname() of its own (it relies on the naming_series
autoname rule), so defining one here takes precedence via override_doctype_class.
"""

import frappe
from frappe import _
from frappe.model.naming import set_name_by_naming_series

from erpnext.projects.doctype.project.project import Project as _ERPNextProject

PROJECT_ID_MODE = "Project ID"


def project_naming_mode():
	return frappe.db.get_single_value("BuildSuite Core Settings", "project_naming") or PROJECT_ID_MODE


class BuildSuiteProject(_ERPNextProject):
	def autoname(self):
		mode = project_naming_mode()
		if mode == PROJECT_ID_MODE:
			project_id = (self.get("custom_project_id") or "").strip()
			if not project_id:
				frappe.throw(_("Project ID is required."))
			self.name = project_id
			return
		# Otherwise treat the setting as a naming series.
		self.naming_series = mode
		set_name_by_naming_series(self)


def reject_duplicate_project_id(doc, method=None):
	"""In Project-ID naming mode the record name IS the Project ID, so a duplicate id
	collides on the primary key and would surface as a raw DB error. Reject it up
	front with a clean message (Frappe's own unique-field check can't catch it here,
	since it excludes the row whose name equals the id)."""
	if not doc.is_new() or project_naming_mode() != PROJECT_ID_MODE:
		return
	project_id = (doc.get("custom_project_id") or "").strip()
	if project_id and frappe.db.exists("Project", project_id):
		frappe.throw(_("A project with ID {0} already exists.").format(project_id))
