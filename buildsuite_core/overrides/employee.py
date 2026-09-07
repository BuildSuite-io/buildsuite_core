# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Field Employee naming.

The Employee code doubles as the record `name`, as `custom_project_id` does for
Project: an entered code IS the name; with none the `HR-EMP-` series names the
record and is copied back, so the code is never blank.

Only field employees are named this way — office staff keep ERPNext's naming.

The code rides in ERPNext's `employee` field, already a mirror of the name, so
every existing worker carries it. It is hidden on the Desk form, so a code can
only be entered in the Vue app.
"""

import re

import frappe
from erpnext.setup.doctype.employee.employee import Employee as _ERPNextEmployee
from frappe import _
from frappe.model.naming import set_name_by_naming_series

# The code lands in /field-employees/<id>, built by plain string interpolation, so
# anything with URL meaning breaks the route. Frappe itself rejects only < and >.
CODE_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class BuildSuiteEmployee(_ERPNextEmployee):
	def autoname(self):
		if not self.get("is_labour"):
			return super().autoname()

		code = (self.get("employee") or "").strip()
		if code:
			if not CODE_PATTERN.match(code):
				frappe.throw(_("Employee code can use only letters, numbers, dot, dash and underscore."))
			# The code is the primary key, so a clash would surface as a raw DB error.
			if frappe.db.exists("Employee", code):
				frappe.throw(_("A worker with code {0} already exists.").format(code))
			self.employee = code
			self.name = code
			return

		set_name_by_naming_series(self)
		# Surface the generated name AS the code, or the field reads blank in the app.
		self.employee = self.name
