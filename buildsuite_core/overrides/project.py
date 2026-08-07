# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project naming override.

The Frappe record `name` for a Project is controlled by the BuildSuite Core
Settings "Project Naming" select (the mode):

  - "Project ID"  -> the name IS the entered Project ID (custom_project_id). The
                     field is already required + unique, so the id doubles as the
                     record key.
  - "Name Series" -> the name is generated from the naming series chosen on the New
                     Project form (the project's own `naming_series` field), falling
                     back to the Project doctype's default series.

ERPNext's Project has no autoname() of its own (it relies on the naming_series
autoname rule), so defining one here takes precedence via override_doctype_class.
"""

import frappe
from erpnext.projects.doctype.project.project import Project as _ERPNextProject
from frappe import _
from frappe.model.naming import set_name_by_naming_series

PROJECT_ID_MODE = "Project ID"
NAME_SERIES_MODE = "Name Series"
SETTINGS = "BuildSuite Core Settings"


def project_naming_mode():
	return frappe.db.get_single_value(SETTINGS, "project_naming") or PROJECT_ID_MODE


def default_project_series():
	"""The Project doctype's default naming series (its field default, else the first
	configured option)."""
	field = frappe.get_meta("Project").get_field("naming_series")
	if not field or not field.options:
		return None
	options = [row.strip() for row in field.options.split("\n") if row.strip()]
	return field.default or (options[0] if options else None)


class BuildSuiteProject(_ERPNextProject):
	def autoname(self):
		# A Project ID always wins: when one is entered it IS the record name, in
		# either naming mode. The ID is optional — with none entered, the name comes
		# from the naming series (the per-project pick, else the doctype default).
		project_id = (self.get("custom_project_id") or "").strip()
		if project_id:
			self.custom_project_id = project_id
			self.name = project_id
			return

		if not self.naming_series:
			self.naming_series = default_project_series()
		if self.naming_series:
			set_name_by_naming_series(self)
			# No ID was entered, so surface the series-generated name AS the Project ID —
			# otherwise the field stays NULL and the Vue views show a blank ID. The name is
			# the primary key (unique), so this keeps the unique index intact.
			self.custom_project_id = self.name
			return
		self.custom_project_id = None  # keep it NULL (not "") so the unique index holds
		frappe.throw(_("Enter a Project ID or configure a naming series."))


def reject_duplicate_project_id(doc, method=None):
	"""When a Project ID is entered it becomes the record name, so a duplicate collides
	on the primary key and would surface as a raw DB error. Reject it up front with a
	clean message (Frappe's own unique-field check can't catch it here, since it
	excludes the row whose name equals the id)."""
	if not doc.is_new():
		return
	project_id = (doc.get("custom_project_id") or "").strip()
	if project_id and frappe.db.exists("Project", project_id):
		frappe.throw(_("A project with ID {0} already exists.").format(project_id))
