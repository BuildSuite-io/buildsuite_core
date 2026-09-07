# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Field Employee naming.

The Employee code doubles as the record `name`, as `custom_project_id` does for
Project: an entered code IS the name; with none the `HR-EMP-` series names the
record and is copied back, so the code is never blank.

The code rides in ERPNext's `employee` field, already a mirror of the name, so
every existing worker carries it. It is hidden on the Desk form, so a code can
only be entered in the Vue app.
"""

import frappe
from erpnext.setup.doctype.employee.employee import Employee as _ERPNextEmployee
from frappe import _
from frappe.model.naming import set_name_by_naming_series

# Frappe rejects only < and >; these two break the /field-employees/<id> route.
UNSAFE_IN_CODE = ("/", "#")


class BuildSuiteEmployee(_ERPNextEmployee):
	def autoname(self):
		code = (self.get("employee") or "").strip()
		if code:
			if any(char in code for char in UNSAFE_IN_CODE):
				frappe.throw(_("Employee code cannot contain {0}.").format(" or ".join(UNSAFE_IN_CODE)))
			# The code is the primary key, so a clash would surface as a raw DB error.
			if frappe.db.exists("Employee", code):
				frappe.throw(_("A worker with code {0} already exists.").format(code))
			self.employee = code
			self.name = code
			return

		set_name_by_naming_series(self)
		# Surface the generated name AS the code, or the field reads blank in the app.
		self.employee = self.name
