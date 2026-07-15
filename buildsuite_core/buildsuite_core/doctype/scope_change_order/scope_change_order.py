# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today


class ScopeChangeOrder(Document):
	def validate(self):
		self._set_company()
		if not self.raised_by:
			self.raised_by = frappe.session.user
		if not self.raised_date:
			self.raised_date = today()
		if not self.status:
			self.status = "Pending Approval"

	def _set_company(self):
		if self.company:
			return
		if self.project:
			self.company = frappe.db.get_value("Project", self.project, "company")
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)
